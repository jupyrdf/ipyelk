*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}examples${/}${NODE MENAGERIE}


*** Test Cases ***
12_Node_Menagerie
    Example Should Restart-and-Run-All    ${NODE MENAGERIE}
