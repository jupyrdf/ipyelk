*** Settings ***
Resource            _resources/keywords/Server.robot
Resource            _resources/keywords/Lab.robot

Suite Setup         Setup Server and Browser
Suite Teardown      Tear Down Everything
Test Setup          Maybe Reset Application State

Force Tags          os:${os.lower()}
