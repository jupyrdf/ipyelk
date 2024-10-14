*** Settings ***
Library     OperatingSystem
Library     SeleniumLibrary
Resource    Browser.robot
Resource    ../variables/Lab.robot
Resource    ../variables/Browser.robot


*** Keywords ***
Open JupyterLab
    Set Environment Variable    MOZ_HEADLESS    ${HEADLESS}
    ${options} =    Evaluate
    ...    selenium.webdriver.FirefoxOptions()
    ...    selenium.webdriver
    ${options.binary_location} =    Set Variable    ${FIREFOX}
    Call Method    ${options}    set_preference    ui.prefersReducedMotion    ${1}
    Call Method    ${options}    set_preference    devtools.console.stdout.content    ${True}

    ${service args} =    Create List    --log    info
    Set Global Variable    ${NEXT BROWSER}    ${NEXT BROWSER.__add__(1)}
    ${geckolog} =    Set Variable    ${OUTPUT DIR}${/}logs${/}geckodriver-${NEXT BROWSER}.log
    # normalize windows slashes
    ${geckolog} =    Set Variable    ${geckolog.replace('\\', '/')}

    Open Browser
    ...    about:blank
    ...    headlessfirefox
    ...    options=${options}
    ...    service=log_output='${geckolog}'; executable_path='${GECKODRIVER}'
    Wait Until Keyword Succeeds    3x    5s    Wait For Splash

Wait For Splash
    Go To    ${URL}lab?reset&token=${TOKEN}
    Set Window Size    1920    1080
    Wait Until Element Is Visible    ${SPLASH}    timeout=30s
    Wait Until Element Is Not Visible    ${SPLASH}    timeout=10s
    Execute Javascript    window.onbeforeunload \= function (){}

Try to Close All Tabs
    Wait Until Keyword Succeeds    5x    50ms    Close All Tabs

Close All Tabs
    Accept Default Dialog Option
    Lab Command    Close All Tabs
    Accept Default Dialog Option

Wait For All Cells To Run
    [Arguments]    ${timeout}=10s
    Scroll To Notebook Bottom
    Wait Until Element Does Not Contain    ${JLAB XP LAST CODE PROMPT}    [*]:    timeout=${timeout}
    Wait Until Element is Visible    ${JLAB XP KERNEL IDLE}    timeout=${timeout}
    Scroll To Notebook Top

Scroll To Notebook Bottom
    Ensure Notebook Window Scrollbar is Open
    Click Element    ${JLAB CSS WINDOW SCROLL} li:last-child

Scroll To Notebook Cell
    [Arguments]    ${index}=${0}
    Ensure Notebook Window Scrollbar is Open
    Click Element    ${JLAB CSS WINDOW SCROLL} li:nth-child(${index})

Scroll To Notebook Top
    Ensure Notebook Window Scrollbar is Open
    Click Element    ${JLAB CSS WINDOW SCROLL} li:first-child

Click JupyterLab Menu
    [Documentation]    Click a top-level JupyterLab menu bar item with by ``label``,
    ...    e.g. File, Help, etc.
    [Arguments]    ${label}
    ${xpath} =    Set Variable    ${JLAB XP TOP}${JLAB XP MENU LABEL}\[text() = '${label}']
    Wait Until Element Is Visible    ${xpath}
    Mouse Over    ${xpath}
    Click Element    ${xpath}

Click JupyterLab Menu Item
    [Documentation]    Click a currently-visible JupyterLab menu item by ``label``.
    [Arguments]    ${label}
    ${item} =    Set Variable    ${JLAB XP MENU ITEM LABEL}\[text() = '${label}']
    Wait Until Element Is Visible    ${item}
    Mouse Over    ${item}
    Click Element    ${item}

Open With JupyterLab Menu
    [Documentation]    Click into a ``menu``, then a series of ``submenus``
    [Arguments]    ${menu}    @{submenus}
    Click JupyterLab Menu    ${menu}
    FOR    ${submenu}    IN    @{submenus}
        Click JupyterLab Menu Item    ${submenu}
    END

Ensure Notebook Window Scrollbar is Open
    ${els} =    Get WebElements    ${JLAB CSS WINDOW SCROLL}
    IF    not ${els.__len__()}    Click Element    ${JLAB CSS WINDOW TOGGLE}

Ensure File Browser is Open
    ${sel} =    Set Variable    css:.lm-TabBar-tab[data-id="filebrowser"]:not(.lm-mod-current)
    ${els} =    Get WebElements    ${sel}
    IF    ${els.__len__()}    Click Element    ${sel}

Ensure Sidebar Is Closed
    [Arguments]    ${side}=left
    ${els} =    Get WebElements    css:#jp-${side}-stack
    IF    ${els.__len__()} and ${els[0].is_displayed()}
        Wait Until Keyword Succeeds    3x    0.5s    Click Element    css:.jp-mod-${side} .lm-TabBar-tab.lm-mod-current
    END

Open Context Menu for File
    [Arguments]    ${file}
    Ensure File Browser is Open
    Click Element    css:jp-button[data-command="filebrowser:refresh"]
    ${selector} =    Set Variable    xpath://span[@class='jp-DirListing-itemText']//span\[text() = '${file}']
    Wait Until Element Is Visible    ${selector}
    Open Context Menu    ${selector}

Rename Jupyter File
    [Arguments]    ${old}    ${new}
    Open Context Menu for File    ${old}
    Mouse Over    ${MENU RENAME}
    Click Element    ${MENU RENAME}
    Press Keys    None    CTRL+a
    Press Keys    None    ${new}
    Press Keys    None    RETURN

Input Into Dialog
    [Arguments]    ${text}
    Wait For Dialog
    Click Element    ${DIALOG INPUT}
    Input Text    ${DIALOG INPUT}    ${text}
    Click Element    ${DIALOG ACCEPT}

Open ${file} in ${editor}
    Open Context Menu for File    ${file}
    Mouse Over    ${MENU OPEN WITH}
    Wait Until Element Is Visible    ${editor}
    Mouse Over    ${editor}
    Click Element    ${editor}

Clean Up After Working With Files
    [Arguments]    @{files}
    FOR    ${file}    IN    @{files}
        ${src}    ${name} =    Split Path    ${file}
        Remove File    ${OUTPUT DIR}${/}home${/}${name}
    END
    Maybe Reset Application State

Wait For Dialog
    Wait Until Element Is Visible    ${DIALOG WINDOW}    timeout=40s

Gently Reset Workspace
    Try to Close All Tabs

Enter Cell Editor
    [Arguments]    ${cell_nr}    ${line}=1
    Click Element    css:.jp-Cell:nth-child(${cell_nr}) .CodeMirror-line:nth-child(${line})
    Wait Until Page Contains Element    css:.jp-Cell:nth-child(${cell_nr}) .CodeMirror-focused

Place Cursor In Cell Editor At
    [Arguments]    ${cell_nr}    ${line}    ${character}
    Enter Cell Editor    ${cell_nr}    ${line}
    Execute JavaScript
    ...    return document.querySelector('.jp-Cell:nth-child(${cell_nr}) .CodeMirror').CodeMirror.setCursor({line: ${line} - 1, ch: ${character}})

Enter File Editor
    Click Element    css:.jp-FileEditor .CodeMirror
    Wait Until Page Contains Element    css:.jp-FileEditor .CodeMirror-focused

Place Cursor In File Editor At
    [Arguments]    ${line}    ${character}
    Enter File Editor
    Execute JavaScript
    ...    return document.querySelector('.jp-FileEditor .CodeMirror').CodeMirror.setCursor({line: ${line} - 1, ch: ${character}})

Open Context Menu Over
    [Arguments]    ${sel}
    Wait Until Keyword Succeeds    10 x    0.1 s    Mouse Over    ${sel}
    Wait Until Keyword Succeeds    10 x    0.1 s    Open Context Menu    ${sel}

Open File
    [Arguments]    ${file}    ${editor}=${MENU EDITOR}
    ${parent}    ${name} =    Split Path    ${file}
    Copy File    ${file}    ${OUTPUT DIR}${/}home${/}${name}
    Open ${name} in ${editor}
    Capture Page Screenshot    00-opened.png

Open in Advanced Settings
    [Arguments]    ${plugin id}
    Lab Command    Advanced Settings Editor
    ${sel} =    Set Variable    css:[data-id="${plugin id}"]
    Wait Until Element Is Visible    ${sel}
    Click Element    ${sel}
    Wait Until Page Contains    System Defaults

Set Editor Content
    [Arguments]    ${text}    ${css}=${EMPTY}
    Execute JavaScript    return document.querySelector('${css} .CodeMirror').CodeMirror.setValue(`${text}`)

Get Editor Content
    [Arguments]    ${css}=${EMPTY}
    ${content} =    Execute JavaScript    return document.querySelector('${css} .CodeMirror').CodeMirror.getValue()
    RETURN    ${content}

Close JupyterLab
    Close All Browsers

Open Command Palette
    Press Keys    id:main    ${ACCEL}+SHIFT+c
    Wait Until Element Is Visible    ${CMD PALETTE INPUT}
    Wait Until Keyword Succeeds    3x    1s    Click Element    ${CMD PALETTE INPUT}

Enter Command Name
    [Arguments]    ${cmd}
    Open Command Palette
    Input Text    ${CMD PALETTE INPUT}    ${cmd}

Lab Command
    [Arguments]    ${cmd}
    Enter Command Name    ${cmd}
    Wait Until Element Is Visible    ${CMD PALETTE ITEM ACTIVE}
    Wait Until Keyword Succeeds    5x    0.5s    Click Element    ${CMD PALETTE ITEM ACTIVE}

Restart and Run All
    Lab Command    Clear Outputs of All Cells
    Lab Command    Restart Kernel and Run All Cells
    Accept Default Dialog Option
    Ensure Sidebar Is Closed
    Run Keyword and Ignore Error    Wait Until Element Contains    ${JLAB XP LAST CODE PROMPT}    [*]:

Maybe Reset Application State
    [Documentation]    when running under pabot, it's not neccessary to reset, saves ~10s/test
    ${in pabot} =    Get Variable Value    ${PABOT ID}    NOPE
    Try to Close All Tabs
    IF    "${in pabot}" == "NOPE"    Reset Application State

Reset Application State
    Try to Close All Tabs
    Accept Default Dialog Option
    Ensure All Kernels Are Shut Down
    Lab Command    Reset Application State
    Wait Until Keyword Succeeds    3x    5s    Wait For Splash

Accept Default Dialog Option
    [Documentation]    Accept a dialog, if it exists
    ${el} =    Get WebElements    ${CSS DIALOG OK}
    IF    ${el.__len__()}    Click Element    ${CSS DIALOG OK}

Ensure All Kernels Are Shut Down
    Enter Command Name    Shut Down All Kernels
    ${els} =    Get WebElements    ${CMD PALETTE ITEM ACTIVE}
    ${accept} =    Set Variable    css:.jp-mod-accept.jp-mod-warn
    IF    ${els.__len__()}
        Wait Until Element is Visible    ${CMD PALETTE ITEM ACTIVE}
        Click Element    ${CMD PALETTE ITEM ACTIVE}
        Wait Until Element Is Visible    ${accept}
        Click Element    ${accept}
    END

Page Should Not Contain Contain Standard Errors
    [Arguments]    ${prefix}=${EMPTY}    ${exceptions}=${None}
    ${errors} =    Get WebElements    ${JLAB XP STDERR}
    FOR    ${error}    IN    @{errors}
        ${error_text} =    Get Text    ${error}
        Log    ${error_text}    level=ERROR
    END
    Page Should Not Contain Element    ${JLAB XP STDERR}
