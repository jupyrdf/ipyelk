*** Settings ***
Documentation       JupyterLab compatibility utilities

Library             SeleniumLibrary
Resource            ../variables/Lab.robot


*** Variables ***
${LAB VIRTUAL SCROLLING}    ${TRUE}


*** Keywords ***
Get Cell Count
    IF    ${LAB VIRTUAL SCROLLING}
        Ensure Notebook Window Scrollbar is Open
        ${cells} =    Get WebElements    ${JLAB CSS WINDOW SCROLL} li
    ELSE
        ${cells} =    Get WebElements    ${JLAB CSS CELL}
    END

    RETURN    ${cells.__len__()}

Scroll To First Cell
    Scroll To Cell    1

Scroll To Last Cell
    ${cell_count} =    Get Cell Count
    Scroll To Cell    ${cell_count}

Scroll To Cell
    [Arguments]    ${n}
    ${cell} =    Set Variable    ${JLAB CSS CELL}:nth-child(${n})

    IF    ${LAB_VIRTUAL_SCROLLING}
        Ensure Notebook Window Scrollbar is Open
        Click Element    ${JLAB CSS WINDOW SCROLL} li:nth-child(${n})
    ELSE
        Execute Javascript
        ...    document.querySelector(".jp-Cell:nth-child(${n})").scrollIntoView()
    END

Ensure Notebook Window Scrollbar is Open
    ${els} =    Get WebElements    ${JLAB CSS WINDOW SCROLL}
    IF    not ${els.__len__()}    Click Element    ${JLAB CSS WINDOW TOGGLE}
