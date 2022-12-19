*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}examples${/}08_Simulation_App


*** Test Cases ***
08_Simulation_App
    [Tags]    gh:48
    Example Should Restart-and-Run-All    ${SIM APP}
    # not worth counting anything, as is basically non-deterministic
    Wait Until Computed Element Styles Are    5x    1s    rect.elknode    stroke=rgba(0, 0, 0, 0)
    Wait Until Computed Element Styles Are    5x    1s    .down path    strokeDasharray=4px    stroke=rgb(255, 0, 0)
    Wait Until Computed Element Styles Are    5x    1s    .elkedge    fontWeight=700
