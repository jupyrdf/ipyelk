*** Settings ***
Documentation       JupyterLab compatibility utilities

Library             Collections
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
    IF    ${LAB_VIRTUAL_SCROLLING}
        Ensure Notebook Window Scrollbar is Open
        ${items} =    Get WebElements    ${JLAB CSS WINDOW SCROLL} li
        IF    ${items.__len__()} >= ${n}
            ${index} =    Evaluate    int(${n}) - 1
            ${item} =    Get From List    ${items}    ${index}
            Execute Javascript
            ...    arguments[0].scrollIntoView({block: "center"})
            ...    ARGUMENTS    ${item}
            Execute Javascript
            ...    arguments[0].click()
            ...    ARGUMENTS    ${item}
        ELSE
            Scroll Rendered Cell To View    ${n}
        END
    ELSE
        Scroll Rendered Cell To View    ${n}
    END

Scroll Rendered Cell To View
    [Arguments]    ${n}
    ${cells} =    Get WebElements    ${JLAB CSS CELL}
    ${count} =    Get Length    ${cells}
    IF    ${count} >= ${n}
        ${index} =    Evaluate    int(${n}) - 1
    ELSE
        ${index} =    Evaluate    int(${count}) - 1
    END
    ${cell} =    Get From List    ${cells}    ${index}
    Execute Javascript
    ...    arguments[0].scrollIntoView({block: "center"})
    ...    ARGUMENTS    ${cell}

Ensure Notebook Window Scrollbar is Open
    ${els} =    Get WebElements    ${JLAB CSS WINDOW SCROLL}
    IF    not ${els.__len__()}
        ${toggles} =    Get WebElements    ${JLAB CSS WINDOW TOGGLE}
        IF    ${toggles.__len__()}
            Click Element    ${JLAB CSS WINDOW TOGGLE}
        ELSE
            Set Suite Variable    ${LAB VIRTUAL SCROLLING}    ${FALSE}
        END
    END
