*** Settings ***
Resource          CLI.robot
Library           SeleniumLibrary
Library           Collections
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

Computed Element Style Should Be
    [Arguments]    ${css selector}    &{styles}
    [Documentation]    Check whether the element style has all the given camelCase-value pairs.
    ...    Further, some values get translated, e.g. `red` -> `rgb(255, 0, 0)`
    ${map} =    Set Variable    return window.getComputedStyle(document.querySelector(`${css selector}`))
    ${observed} =    Create Dictionary
    ${all} =    Execute Javascript    ${map}
    FOR    ${key}    ${value}    IN    &{styles}
        ${computed} =    Execute JavaScript    ${map}\[`${key}`]
        Set To Dictionary    ${observed}    ${key}=${computed}
    END
    Dictionaries Should Be Equal    ${styles}    ${observed}
