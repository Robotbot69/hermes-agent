"""Excluded payloads must not enter the shadow Git object database."""
import os
import subprocess

import pytest

from tools import checkpoint_manager as checkpoints


def test_size_cap_applies_before_snapshot_diff_and_restore_staging(tmp_path, monkeypatch):
    monkeypatch.setattr(checkpoints, 'CHECKPOINT_BASE', tmp_path / 'checkpoints')
    work = tmp_path / 'project'
    work.mkdir()
    small = work / '[small].txt'
    small.write_text('original')
    large = work / 'large.data'
    large.write_bytes(os.urandom(1024 * 1024 + 1))
    manager = checkpoints.CheckpointManager(enabled=True, max_file_size_mb=1)
    assert manager.ensure_checkpoint(str(work))
    target = manager.list_checkpoints(str(work))[0]['hash']
    small.write_text('agent edit')
    manager.record_agent_write(str(small))
    assert manager.diff(str(work), target)['success']
    assert manager.restore(str(work), target, safe=True)['success']
    assert small.read_text() == 'original'
    assert large.stat().st_size == 1024 * 1024 + 1
    ok, objects, error = checkpoints._run_git(
        ['cat-file', '--batch-all-objects', '--batch-check=%(objecttype) %(objectsize)'],
        checkpoints._store_path(), str(work))
    assert ok, error
    assert all(int(line.split()[1]) <= 1024 * 1024
               for line in objects.splitlines() if line.startswith('blob '))


def test_unborn_nested_repo_does_not_block_create_and_delete_snapshots(tmp_path, monkeypatch):
    monkeypatch.setattr(checkpoints, 'CHECKPOINT_BASE', tmp_path / 'checkpoints')
    work = tmp_path / 'project'
    work.mkdir()
    small = work / 'ordinary.txt'
    small.write_text('original')
    nested = work / 'unborn'
    nested.mkdir()
    subprocess.run(['git', 'init', '--quiet', str(nested)], check=True)
    (nested / 'uncommitted.txt').write_text('not captured')
    manager = checkpoints.CheckpointManager(enabled=True)
    assert manager.ensure_checkpoint(str(work))
    target = manager.list_checkpoints(str(work))[0]['hash']
    manager.record_agent_write(str(small))
    small.unlink()
    created = work / ' leading\nname.txt'
    created.write_text('new file')
    manager.record_agent_write(str(created))
    manager.new_turn()
    assert manager.ensure_checkpoint(str(work))
    assert manager.restore(str(work), target, safe=True)['success']
    assert small.read_text() == 'original'
    assert not created.exists()
    assert (nested / 'uncommitted.txt').read_text() == 'not captured'


def test_directory_replaced_by_symlink_preserves_literal_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(checkpoints, 'CHECKPOINT_BASE', tmp_path / 'checkpoints')
    work = tmp_path / 'project'
    work.mkdir()
    nested = work / 'd'
    nested.mkdir()
    child = nested / 'file.txt'
    child.write_text('original')
    manager = checkpoints.CheckpointManager(enabled=True)
    assert manager.ensure_checkpoint(str(work))
    child.unlink()
    nested.rmdir()
    (work / 'target').mkdir()
    nested.symlink_to('target', target_is_directory=True)
    manager.new_turn()
    assert manager.ensure_checkpoint(str(work))
    target = manager.list_checkpoints(str(work))[0]['hash']
    ok, tree, _ = checkpoints._run_git(['ls-tree', '-r', target], checkpoints._store_path(), str(work))
    assert ok and '120000 blob' in tree and '\td\n' in tree + '\n'
    assert 'd/file.txt' not in tree


def test_safe_restore_preserves_existing_file_when_hash_read_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(checkpoints, 'CHECKPOINT_BASE', tmp_path / 'checkpoints')
    work = tmp_path / 'project'
    work.mkdir()
    path = work / 'private.txt'
    path.write_text('original')
    manager = checkpoints.CheckpointManager(enabled=True)
    assert manager.ensure_checkpoint(str(work))
    target = manager.list_checkpoints(str(work))[0]['hash']
    path.write_text('agent version')
    manager.record_agent_write(str(path))
    original = checkpoints._hash_file
    monkeypatch.setattr(checkpoints, '_hash_file',
                        lambda selected: None if selected == path else original(selected))
    result = manager.restore(str(work), target, safe=True)
    assert result['success']
    assert result['restored_files'] == []
    assert result['skipped_user_edits'] == ['private.txt']
    assert path.read_text() == 'agent version'


@pytest.mark.parametrize('failure', ['nested-head', 'post-size-list', 'post-size-remove'])
def test_real_staging_errors_never_create_successful_snapshot(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(checkpoints, 'CHECKPOINT_BASE', tmp_path / 'checkpoints')
    work = tmp_path / 'project'
    work.mkdir()
    small = work / 'small.txt'
    small.write_text('original')
    if failure == 'nested-head':
        nested = work / 'nested'
        nested.mkdir()
        subprocess.run(['git', 'init', '--quiet', str(nested)], check=True)
    original = checkpoints._run_git
    staged = False
    injected = False

    def fault(args, *rest, **kwargs):
        nonlocal staged, injected
        nested_probe = args[0].startswith('--git-dir=')
        post_list = args[:2] == ['ls-files', '--cached']
        post_remove = args[:2] == ['rm', '--cached'] and '--force' in args
        if ((failure == 'nested-head' and nested_probe)
                or (failure == 'post-size-list' and staged and post_list)
                or (failure == 'post-size-remove' and staged and post_remove)):
            injected = True
            return False, '', 'isolated injected Git failure'
        result = original(args, *rest, **kwargs)
        if args[0] == 'add' and result[0]:
            staged = True
            if failure == 'post-size-remove':
                small.write_bytes(b'x' * (1024 * 1024 + 1))
        return result

    monkeypatch.setattr(checkpoints, '_run_git', fault)
    manager = checkpoints.CheckpointManager(enabled=True, max_file_size_mb=1)
    assert not manager.ensure_checkpoint(str(work))
    assert injected
    assert manager.list_checkpoints(str(work)) == []
