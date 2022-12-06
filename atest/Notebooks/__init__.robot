*** Settings ***
Documentation       Tests with ipyelk notebooks

Resource            ../_resources/keywords/Browser.robot

Suite Setup         Setup Suite For Screenshots    notebooks

Force Tags          ui:notebook
