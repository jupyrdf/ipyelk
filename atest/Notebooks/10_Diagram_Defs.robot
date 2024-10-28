*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}examples${/}${DIAGRAM DEFS}


*** Test Cases ***
10_Logic_Gates
    Example Should Restart-and-Run-All    ${DIAGRAM DEFS}
