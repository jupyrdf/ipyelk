*** Settings ***
Documentation       Keywords for working with browser coverage data

Library             OperatingSystem
Library             SeleniumLibrary
Library             uuid


*** Keywords ***
Get Next Coverage File
    [Documentation]    Get a random filename.
    ${uuid} =    UUID1
    RETURN    ${uuid.__str__()}

Capture Page Coverage
    [Documentation]    Fetch coverage data from the browser.
    [Arguments]    ${name}=${EMPTY}
    IF    not '''${name}'''
        ${name} =    Get Next Coverage File
    END
    ${cov_json} =    Execute Javascript
    ...    return window.__coverage__ && JSON.stringify(window.__coverage__, null, 2)
    IF    ${cov_json}
        Create File    ${OUTPUT DIR}${/}jscov${/}${name}.json    ${cov_json}
        Execute Javascript    window.__coverage__ = {}
    ELSE
        Log    No browser coverage captured    ERROR
    END
