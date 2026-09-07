*** Settings ***
Resource            _resources/keywords/Server.robot
Resource            _resources/keywords/Lab.robot

Suite Setup         Setup Server and Browser
Suite Teardown      Tear Down Everything
Test Setup          Maybe Reset Application State
# a wedged browser or kernel must fail the test, not burn the whole job: the
# Windows runner spent 40 minutes on one stuck notebook before this
Test Timeout        15 minutes

Force Tags          os:${os.lower()}
