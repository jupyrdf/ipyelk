*** Keywords ***
Tag For Pabot
    Set Suite Variable    ${PABOT ID}
    ...    ${CALLER_ID[:3]}_${PABOTEXECUTIONPOOLID}_${PABOTQUEUEINDEX}
    ...    children=${True}
    Set Tags
    ...    pabot:${PABOT ID}
