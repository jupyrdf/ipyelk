*** Keywords ***
Which
    [Arguments]    ${cmd}
    ${path} =    Evaluate    __import__("shutil").which("${cmd}")
    [Return]    ${path}
