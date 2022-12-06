*** Settings ***
Resource    CLI.robot
Library     SeleniumLibrary
Library     Collections
Resource    ../variables/Browser.robot


*** Keywords ***
Setup Suite For Screenshots
    [Arguments]    ${folder}
    Set Screenshot Directory    ${SCREENS ROOT}${/}${folder}

Computed Element Style Should Be
    [Documentation]    Check whether the element style has all the given camelCase-value pairs.
    ...    Further, some values get translated, e.g. `red` -> `rgb(255, 0, 0)`
    [Arguments]    ${css selector}    &{styles}
    ${map} =    Set Variable    return window.getComputedStyle(document.querySelector(`${css selector}`))
    ${observed} =    Create Dictionary
    ${all} =    Execute Javascript    ${map}
    FOR    ${key}    ${value}    IN    &{styles}
        ${computed} =    Execute JavaScript    ${map}\[`${key}`]
        Set To Dictionary    ${observed}    ${key}=${computed}
    END
    Dictionaries Should Be Equal    ${styles}    ${observed}
