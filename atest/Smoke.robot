*** Settings ***
Suite Setup       Setup Suite For Screenshots    smoke
Resource          _resources/keywords/Browser.robot
Resource          _resources/keywords/Lab.robot

*** Test Cases ***
Lab Loads
    Capture Page Screenshot    00-smoke.png
