import json
import mock
import os
import pytest
import sys

import scriptworker.client
from scriptworker.exceptions import ScriptWorkerTaskException, ScriptWorkerException
from treescript.test import noop_async, noop_sync, read_file, tmpdir, BASE_DIR
import treescript.script as script

assert tmpdir  # silence flake8

# helper constants, fixtures, functions {{{1
EXAMPLE_CONFIG = os.path.join(BASE_DIR, 'config_example.json')
SSL_CERT = os.path.join(BASE_DIR, "signingscript", "data", "host.cert")


def get_conf_file(tmpdir, **kwargs):
    conf = json.loads(read_file(EXAMPLE_CONFIG))
    conf.update(kwargs)
    conf['work_dir'] = os.path.join(tmpdir, 'work')
    conf['artifact_dir'] = os.path.join(tmpdir, 'artifact')
    path = os.path.join(tmpdir, "new_config.json")
    with open(path, "w") as fh:
        json.dump(conf, fh)
    return path


async def die_async(*args, **kwargs):
    raise ScriptWorkerTaskException("Expected exception.")


# SigningContext {{{1
def test_tree_context():
    c = script.TreeContext()
    c.write_json()


# async_main {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    'robustcheckout_works,raises',
    ((
        False, ScriptWorkerException
    ), (
        True, None
    ))
)
async def test_async_main(tmpdir, mocker, robustcheckout_works, raises):

    async def fake_validate_robustcheckout(_):
        return robustcheckout_works

    mocker.patch.object(scriptworker.client, 'get_task', new=noop_sync)
    mocker.patch.object(script, 'validate_task_schema', new=noop_sync)
    mocker.patch.object(script, 'task_action_types', new=noop_sync)
    mocker.patch.object(script, 'validate_robustcheckout_works', new=fake_validate_robustcheckout)
    mocker.patch.object(script, 'log_mercurial_version', new=noop_async)
    mocker.patch.object(script, 'checkout_repo', new=noop_async)
    # mocker.patch.object(script, 'task_cert_type', new=noop_sync)
    # mocker.patch.object(script, 'task_signing_formats', new=noop_sync)
    # mocker.patch.object(script, 'get_token', new=noop_async)
    # mocker.patch.object(script, 'build_filelist_dict', new=fake_filelist_dict)
    # mocker.patch.object(script, 'copy_to_dir', new=noop_sync)
    # mocker.patch.object(script, 'sign', new=fake_sign)
    context = mock.MagicMock()
    # context.config = {'work_dir': tmpdir, 'ssl_cert': None, 'artifact_dir': tmpdir}
    if raises:
        with pytest.raises(raises):
            await script.async_main(context)
    else:
        await script.async_main(context)


# get_default_config {{{1
def test_get_default_config():
    parent_dir = os.path.dirname(os.getcwd())
    c = script.get_default_config()
    assert c['work_dir'] == os.path.join(parent_dir, 'work_dir')


# usage {{{1
def test_usage():
    with pytest.raises(SystemExit):
        script.usage()


# main {{{1
def test_main_missing_args(mocker):
    mocker.patch.object(sys, 'argv', new=[__file__])
    with pytest.raises(SystemExit):
        script.main()


def test_main_argv(tmpdir, mocker):
    conf_file = get_conf_file(tmpdir, verbose=False, ssl_cert=None)
    mocker.patch.object(sys, 'argv', new=[__file__, conf_file])
    mocker.patch.object(script, 'async_main', new=noop_async)
    script.main()


def test_main_noargv(tmpdir, mocker):
    conf_file = get_conf_file(tmpdir, verbose=True, ssl_cert=SSL_CERT)
    mocker.patch.object(script, 'async_main', new=die_async)
    with pytest.raises(SystemExit):
        script.main(config_path=conf_file)
