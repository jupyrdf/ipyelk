*** Settings ***
Resource          CLI.robot
Library           SeleniumLibrary
Resource          ../variables/Browser.robot

*** Keywords ***
Setup Suite For Screenshots
    [Arguments]    ${folder}
    Set Screenshot Directory    ${SCREENS ROOT}${/}${folder}

Get Firefox Binary
    [Documentation]    Get Firefox path from the environment... or hope for the best
    ${from which} =    Which    firefox
    ${firefox} =    Set Variable If    "%{FIREFOX_BINARY}"    %{FIREFOX_BINARY}    ${from which}
    [Return]    ${firefox}
