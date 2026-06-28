/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";

patch(NavBar.prototype, {
    toggleFullAppsMenu() {
        this.state.isAllAppsMenuOpened = !this.state.isAllAppsMenuOpened;
    },

    closeFullAppsMenu() {
        this.state.isAllAppsMenuOpened = false;
    },

    async onFullAppsMenuItemClick(app) {
        await this.menuService.selectMenu(app);
        this.closeFullAppsMenu();
    },
});
