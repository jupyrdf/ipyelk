*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}examples${/}04_Interactive


*** Test Cases ***
04_Interactive
    Example Should Restart-and-Run-All    ${INTERACTIVE}
    # not worth counting anything, as is basically non-deterministic
