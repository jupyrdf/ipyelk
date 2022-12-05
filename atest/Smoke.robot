*** Settings ***
Resource        _resources/keywords/Browser.robot
Resource        _resources/keywords/Lab.robot

Suite Setup     Setup Suite For Screenshots    smoke


*** Test Cases ***
Lab Loads
    Capture Page Screenshot    00-smoke.png
