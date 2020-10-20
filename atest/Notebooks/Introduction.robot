*** Settings ***
Documentation     Introduction
Suite Setup       Setup Suite For Screenshots    notebook-introduction
Resource          ../_resources/keywords/Browser.robot
Resource          ../_resources/keywords/Lab.robot
Resource          ../_resources/keywords/IPyElk.robot

*** Variables ***
${INTRODUCTION}          00_Introduction

*** Test Cases ***
Introduction
    Open IPyElk Notebook    ${INTRODUCTION}
    Restart and Run All
    Wait For All Cells To Run    60s
    Capture All Code Cells
    Page Should Not Contain Element    ${JLAB XP STDERR}
    [Teardown]    Clean up after Working with file    ${INTRODUCTION}.ipynb
