*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}examples${/}07_Simulation


*** Test Cases ***
07_Simulation
    Example Should Restart-and-Run-All    ${SIM PLUMBING}
    # not worth counting anything, as is basically non-deterministic
