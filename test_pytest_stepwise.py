import pytest


@pytest.fixture
def stepwise_testdir(testdir):
    # Rather than having to modify our testfile between tests, we introduce
    # a flag for wether or not the second test should fail.
    testdir.makeconftest('''
def pytest_addoption(parser):
    group = parser.getgroup('general')
    group.addoption('--fail', action='store_true', dest='fail')
    group.addoption('--fail-last', action='store_true', dest='fail_last')
''')

    # Create a simple test suite.
    testdir.makepyfile(test_stepwise='''
def test_success_before_fail():
    assert 1

def test_fail_on_flag(request):
    assert not request.config.getvalue('fail')

def test_success_after_fail():
    assert 1

def test_fail_last_on_flag(request):
    assert not request.config.getvalue('fail_last')

def test_success_after_last_fail():
    assert 1
''')

    return testdir


@pytest.fixture
def error_testdir(testdir):
    testdir.makepyfile(test_stepwise='''
def test_error(nonexisting_fixture):
    assert 1

def test_success_after_fail():
    assert 1
''')

    return testdir


def test_run_without_stepwise(stepwise_testdir):
    result = stepwise_testdir.runpytest('-v', '--strict', '--fail')

    assert not result.errlines
    result.stdout.fnmatch_lines(['*test_success_before_fail PASSED*'])
    result.stdout.fnmatch_lines(['*test_fail_on_flag FAILED*'])
    result.stdout.fnmatch_lines(['*test_success_after_fail PASSED*'])


def test_fail_and_continue_with_stepwise(stepwise_testdir):
    # Run the tests with a failing second test.
    result = stepwise_testdir.runpytest('-v', '--strict', '--stepwise', '--fail')
    assert not result.errlines

    stdout = result.stdout.str()
    # Make sure we stop after first failing test.
    assert 'test_success_before_fail PASSED' in stdout
    assert 'test_fail_on_flag FAILED' in stdout
    assert 'test_success_after_fail' not in stdout

    # "Fix" the test that failed in the last run and run it again.
    result = stepwise_testdir.runpytest('-v', '--strict', '--stepwise')
    assert not result.errlines

    stdout = result.stdout.str()
    # Make sure the latest failing test runs and then continues.
    assert 'test_success_before_fail' not in stdout
    assert 'test_fail_on_flag PASSED' in stdout
    assert 'test_success_after_fail PASSED' in stdout


def test_run_with_skip_option(stepwise_testdir):
    result = stepwise_testdir.runpytest('-v', '--strict', '--stepwise', '--skip',
                                        '--fail', '--fail-last')
    assert not result.errlines

    stdout = result.stdout.str()
    # Make sure first fail is ignore and second fail stops the test run.
    assert 'test_fail_on_flag FAILED' in stdout
    assert 'test_success_after_fail PASSED' in stdout
    assert 'test_fail_last_on_flag FAILED' in stdout
    assert 'test_success_after_last_fail' not in stdout


def test_fail_on_errors(error_testdir):
    result = error_testdir.runpytest('-v', '--strict', '--stepwise')

    assert not result.errlines
    stdout = result.stdout.str()

    assert 'test_error ERROR' in stdout
    assert 'test_success_after_fail' not in stdout
