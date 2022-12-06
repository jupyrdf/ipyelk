*** Variables ***
${SPLASH}                       id:jupyterlab-splash
${CMD PALETTE INPUT}            css:#command-palette .p-CommandPalette-input
${CMD PALETTE ITEM ACTIVE}      css:#command-palette .p-CommandPalette-item.p-mod-active
${JLAB XP TOP}                  //div[@id='jp-top-panel']
${JLAB XP MENU ITEM LABEL}      //div[@class='p-Menu-itemLabel']
${JLAB XP MENU LABEL}           //div[@class='p-MenuBar-itemLabel']
${JLAB XP DOCK TAB}
...                             xpath://div[contains(@class, 'p-DockPanel-tabBar')]//li[contains(@class, 'p-TabBar-tab')]
${JLAB XP CODE CELLS}
...                             xpath://*[contains(@class, 'jp-NotebookPanel-notebook')]/*[contains(@class, 'jp-CodeCell')]
${JLAB XP LAST CODE CELL}       ${JLAB XP CODE CELLS}\[last()]
${JLAB XP LAST CODE PROMPT}     ${JLAB XP LAST CODE CELL}//*[contains(@class, 'jp-InputArea-prompt')]
${JLAB XP STDERR}               xpath://*[@data-mime-type="application/vnd.jupyter.stderr"]
${JLAB XP KERNEL IDLE}          xpath://div[contains(@id, 'jp-main-statusbar')]//span[contains(., "Idle")]
${JLAB CSS VERSION}             css:.jp-About-version
${JLAB CSS CREATE OUTPUT}       .p-Menu-item[data-command="notebook:create-output-view"]
${JLAB CSS LINKED OUTPUT}       .jp-LinkedOutputView
${CSS DIALOG OK}                css:.jp-Dialog .jp-mod-accept
${MENU OPEN WITH}               xpath://div[contains(@class, 'p-Menu-itemLabel')][contains(text(), "Open With")]
# R is missing on purpose (may need to use .)
${MENU RENAME}                  xpath://div[contains(@class, 'p-Menu-itemLabel')][contains(., "ename")]
# N is missing on purpose
${MENU NOTEBOOK}
...                             xpath://div[@id="jp-contextmenu-open-with"]//div[contains(@class, 'p-Menu-itemLabel')][contains(., "otebook")]
${DIALOG WINDOW}                css:.jp-Dialog
${DIALOG INPUT}                 css:.jp-Input-Dialog input
${DIALOG ACCEPT}                css:button.jp-Dialog-button.jp-mod-accept
${STATUSBAR}                    css:div.lsp-statusbar-item
${MENU EDITOR}                  xpath://div[contains(@class, 'p-Menu-itemLabel')][contains(., "Editor")]
${MENU JUMP}
...                             xpath://div[contains(@class, 'p-Menu-itemLabel')][contains(text(), "Jump to definition")]
${MENU SETTINGS}                xpath://div[contains(@class, 'p-MenuBar-itemLabel')][contains(text(), "Settings")]
${MENU EDITOR THEME}
...                             xpath://div[contains(@class, 'p-Menu-itemLabel')][contains(text(), "Text Editor Theme")]
${CM CURSOR}                    css:.CodeMirror-cursor
${CM CURSORS}                   css:.CodeMirror-cursors:not([style='visibility: hidden'])
# settings
${CSS USER SETTINGS}            .jp-SettingsRawEditor-user
${JLAB XP CLOSE SETTINGS}       ${JLAB XP DOCK TAB}\[contains(., 'Settings')]/*[@data-icon='ui-components:close']
