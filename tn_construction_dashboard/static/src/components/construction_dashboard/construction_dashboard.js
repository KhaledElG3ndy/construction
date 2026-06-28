/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

const ARABIC_TEXT = {
    "Dashboard": "لوحة التحكم",
    "Overview of your construction activities": "نظرة عامة على أنشطة البناء",
    "Quick Access": "وصول سريع",
    "Portfolio": "المحفظة",
    "Portfolio Overview": "نظرة عامة على المحفظة",
    "Operations": "العمليات",
    "Execution": "التنفيذ",
    "Execution Stages": "مراحل التنفيذ",
    "Materials": "المواد",
    "Transfers": "التحويلات",
    "Filters": "الفلاتر",
    "View all": "عرض الكل",
    "Scheduled Range": "النطاق الزمني",
    "Project Timeline": "الجدول الزمني للمشروع",
    "Sub Project Stages": "مراحل المشاريع الفرعية",
    "Work Order Status": "حالة أوامر العمل",
    "Material Request Status": "حالة طلبات المواد",
    "Transfer Status": "حالة التحويلات",
    "No Data": "لا توجد بيانات",
    "No material requests": "لا توجد طلبات مواد",
    "No transfers recorded": "لا توجد تحويلات مسجلة",
    "Add sub projects to see timeline": "أضف مشاريع فرعية لعرض الجدول الزمني",
    "All scheduled dates": "كل التواريخ المجدولة",
    "open": "مفتوح",
    "pending": "قيد الانتظار",
    "days": "يوم",
    "Completion": "نسبة الإنجاز",
    "Portfolio span": "نطاق المحفظة",
    "No scheduled sub projects": "لا توجد مشاريع فرعية مجدولة",
    "Projects": "المشاريع",
    "Sub Projects": "المشاريع الفرعية",
    "Material Requests": "طلبات المواد",
    "Phases (WBS)": "المراحل (WBS)",
    "Work Orders": "أوامر العمل",
    "Budgets": "الميزانيات",
    "Active Projects": "المشاريع النشطة",
    "Open Work Orders": "أوامر العمل المفتوحة",
    "Open Materials": "طلبات المواد المفتوحة",
    "Completed Handovers": "التسليمات المكتملة",
    "Draft": "مسودة",
    "Planning": "التخطيط",
    "Procurement": "المشتريات",
    "Construction": "البناء",
    "Handover": "التسليم",
    "Done": "منجز",
    "Waiting Approval": "بانتظار الموافقة",
    "Approved": "معتمد",
    "In Progress": "قيد التنفيذ",
    "Complete": "مكتمل",
    "Material Requested": "تم طلب المواد",
    "Material Arrived": "وصلت المواد",
    "Completed": "مكتمل",
    "Waiting Department Approval": "بانتظار موافقة القسم",
    "Ready for Delivery": "جاهز للتسليم",
    "Internal Transfer": "تحويل داخلي",
    "Cancelled": "ملغي",
    "Unstaged": "بدون مرحلة",
    "Tasks": "المهام",
};

const MODELS = {
    projects: "project.project",
    subProjects: "tn.construction.sub.project",
    budgets: "tn.construction.budget",
    phases: "tn.construction.phase",
    workOrders: "tn.construction.work.order",
    materialRequests: "tn.construction.material.request",
    internalTransfers: "tn.construction.internal.transfer",
    tasks: "project.task",
};

export class ConstructionDashboard extends Component {
    static template = "tn_construction_dashboard.ConstructionDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            counts: {},
            subProjectStages: [],
            workOrderStatuses: [],
            materialStatuses: [],
            transferStatuses: [],
            timeline: { axis: [] },
        });

        onWillStart(async () => {
            await this.loadDashboard();
        });
    }

    get display() {
        return { controlPanel: {} };
    }

    get isRTL() {
        return (user.lang || "").startsWith("ar");
    }

    t(source) {
        if (this.isRTL && ARABIC_TEXT[source]) {
            return ARABIC_TEXT[source];
        }
        return _t(source);
    }

    get text() {
        return {
            quickAccess: this.t("Quick Access"),
            portfolio: this.t("Portfolio"),
            portfolioOverview: this.t("Portfolio Overview"),
            operations: this.t("Operations"),
            execution: this.t("Execution"),
            executionStages: this.t("Execution Stages"),
            materials: this.t("Materials"),
            transfers: this.t("Transfers"),
            dashboard: this.t("Dashboard"),
            dashboardSubtitle: this.t("Overview of your construction activities"),
            filters: this.t("Filters"),
            viewAll: this.t("View all"),
            scheduledRange: this.t("Scheduled Range"),
            projectTimeline: this.t("Project Timeline"),
            subProjectStages: this.t("Sub Project Stages"),
            workOrderStatus: this.t("Work Order Status"),
            materialRequestStatus: this.t("Material Request Status"),
            transferStatus: this.t("Transfer Status"),
            completion: this.t("Completion"),
            noMaterialRequests: this.t("No material requests"),
            noTransfers: this.t("No transfers recorded"),
            addSubProjects: this.t("Add sub projects to see timeline"),
            open: this.t("open"),
            pending: this.t("pending"),
            noData: this.t("No Data"),
            days: this.t("days"),
        };
    }

    async safeCount(model, domain = []) {
        try {
            return await this.orm.searchCount(model, domain);
        } catch {
            return 0;
        }
    }

    async safeReadGroup(model, domain, fields, groupby) {
        try {
            return await this.orm.readGroup(model, domain, fields, groupby);
        } catch {
            return [];
        }
    }

    async safeSearchRead(model, domain = [], fields = [], kwargs = {}) {
        try {
            return await this.orm.searchRead(model, domain, fields, kwargs);
        } catch {
            return [];
        }
    }

    async loadDashboard() {
        const [
            projects,
            subProjects,
            budgets,
            phases,
            workOrders,
            openWorkOrders,
            materialRequests,
            openMaterialRequests,
            internalTransfers,
            openInternalTransfers,
            completedHandovers,
            subProjectStageGroups,
            workOrderGroups,
            materialGroups,
            transferGroups,
            subProjectDates,
        ] = await Promise.all([
            this.safeCount(MODELS.projects),
            this.safeCount(MODELS.subProjects),
            this.safeCount(MODELS.budgets),
            this.safeCount(MODELS.phases),
            this.safeCount(MODELS.workOrders),
            this.safeCount(MODELS.workOrders, [["state", "!=", "completed"]]),
            this.safeCount(MODELS.materialRequests),
            this.safeCount(MODELS.materialRequests, [["state", "!=", "done"]]),
            this.safeCount(MODELS.internalTransfers),
            this.safeCount(MODELS.internalTransfers, [["state", "in", ["draft", "in_progress"]]]),
            this.safeCount(MODELS.subProjects, [["stage", "=", "done"]]),
            this.safeReadGroup(MODELS.subProjects, [], ["stage"], ["stage"]),
            this.safeReadGroup(MODELS.workOrders, [], ["state"], ["state"]),
            this.safeReadGroup(MODELS.materialRequests, [], ["state"], ["state"]),
            this.safeReadGroup(MODELS.internalTransfers, [], ["state"], ["state"]),
            this.safeSearchRead(
                MODELS.subProjects,
                [],
                ["schedule_start_date", "schedule_end_date", "progress"]
            ),
        ]);

        const averageCompletion = this.averageProgress(subProjectDates);

        this.state.counts = {
            projects,
            subProjects,
            budgets,
            phases,
            workOrders,
            openWorkOrders,
            materialRequests,
            openMaterialRequests,
            internalTransfers,
            openInternalTransfers,
            completedHandovers,
            completion: averageCompletion,
            planning: this.groupCount(subProjectStageGroups, "stage", "planning"),
            procurement: this.groupCount(subProjectStageGroups, "stage", "procurement"),
            construction: this.groupCount(subProjectStageGroups, "stage", "construction"),
            handover: this.groupCount(subProjectStageGroups, "stage", "handover"),
            done: this.groupCount(subProjectStageGroups, "stage", "done"),
        };

        this.state.subProjectStages = this.buildStatusRows(
            subProjectStageGroups,
            "stage",
            this.subProjectStageLabels,
            this.stageColors
        );
        this.state.workOrderStatuses = this.buildStatusRows(
            workOrderGroups,
            "state",
            this.workOrderStateLabels,
            this.stateColors
        );
        this.state.materialStatuses = this.buildStatusRows(
            materialGroups,
            "state",
            this.materialStateLabels,
            this.materialColors
        );
        this.state.transferStatuses = this.buildStatusRows(
            transferGroups,
            "state",
            this.transferStateLabels,
            this.transferColors
        );
        this.state.timeline = this.buildTimeline(subProjectDates);
        this.state.loading = false;
    }

    get subProjectStageLabels() {
        return {
            draft: this.t("Draft"),
            planning: this.t("Planning"),
            procurement: this.t("Procurement"),
            construction: this.t("Construction"),
            handover: this.t("Handover"),
            done: this.t("Done"),
        };
    }

    get workOrderStateLabels() {
        return {
            draft: this.t("Draft"),
            material_requested: this.t("Material Requested"),
            material_arrived: this.t("Material Arrived"),
            in_progress: this.t("In Progress"),
            completed: this.t("Completed"),
        };
    }

    get materialStateLabels() {
        return {
            waiting_department_approval: this.t("Waiting Department Approval"),
            in_progress: this.t("In Progress"),
            ready_delivery: this.t("Ready for Delivery"),
            internal_transfer: this.t("Internal Transfer"),
            done: this.t("Done"),
        };
    }

    get transferStateLabels() {
        return {
            draft: this.t("Draft"),
            in_progress: this.t("In Progress"),
            done: this.t("Done"),
            cancelled: this.t("Cancelled"),
        };
    }

    get stageColors() {
        return {
            draft: "#64748b",
            planning: "#0ea5e9",
            procurement: "#f59e0b",
            construction: "#14b8a6",
            handover: "#0f2742",
            done: "#22c55e",
        };
    }

    get stateColors() {
        return {
            draft: "#64748b",
            material_requested: "#f97316",
            material_arrived: "#176b87",
            in_progress: "#0ea5e9",
            completed: "#22c55e",
        };
    }

    get materialColors() {
        return {
            waiting_department_approval: "#f97316",
            in_progress: "#0ea5e9",
            ready_delivery: "#176b87",
            internal_transfer: "#14b8a6",
            done: "#22c55e",
        };
    }

    get transferColors() {
        return {
            draft: "#64748b",
            in_progress: "#0ea5e9",
            done: "#22c55e",
            cancelled: "#ef4444",
        };
    }

    groupCount(groups, field, value) {
        const match = groups.find((group) => group[field] === value);
        return match ? match.__count || match[`${field}_count`] || 0 : 0;
    }

    buildStatusRows(groups, field, labels, colors) {
        if (!groups.length) {
            return [{ label: this.t("No Data"), value: 0, color: "#94a3b8", empty: true }];
        }
        return groups
            .map((group) => {
                const value = group[field] || "";
                return {
                    key: value || "empty",
                    label: labels[value] || value || this.t("Unstaged"),
                    value: group.__count || group[`${field}_count`] || 0,
                    color: colors[value] || "#64748b",
                    domain: value ? [[field, "=", value]] : [[field, "=", false]],
                };
            })
            .sort((a, b) => b.value - a.value);
    }

    averageProgress(subProjects) {
        if (!subProjects.length) {
            return 0;
        }
        const total = subProjects.reduce((sum, subProject) => sum + (subProject.progress || 0), 0);
        return Math.round(total / subProjects.length);
    }

    buildTimeline(subProjects) {
        const starts = subProjects.map((project) => this.parseDate(project.schedule_start_date)).filter(Boolean);
        const ends = subProjects.map((project) => this.parseDate(project.schedule_end_date)).filter(Boolean);
        if (!starts.length || !ends.length) {
            return {
                label: this.t("No scheduled sub projects"),
                days: 0,
                progress: 0,
                axis: [],
            };
        }
        const start = new Date(Math.min(...starts.map((date) => date.getTime())));
        const end = new Date(Math.max(...ends.map((date) => date.getTime())));
        const today = new Date();
        const totalMs = Math.max(end - start, 0);
        const elapsedMs = Math.min(Math.max(today - start, 0), totalMs);
        const days = Math.max(Math.ceil(totalMs / 86400000), 1);
        const progress = totalMs ? Math.round((elapsedMs / totalMs) * 100) : 100;
        return {
            label: this.t("Portfolio span"),
            days,
            progress,
            dateRange: `${this.formatFullDate(start)} - ${this.formatFullDate(end)}`,
            axis: this.buildTimelineAxis(start, end),
        };
    }

    parseDate(value) {
        return value ? new Date(`${value}T00:00:00`) : null;
    }

    formatMonth(value) {
        const locale = this.isRTL ? "ar" : undefined;
        return value.toLocaleDateString(locale, { month: "short", year: "2-digit" });
    }

    formatFullDate(value) {
        const locale = this.isRTL ? "ar" : undefined;
        return value.toLocaleDateString(locale, { month: "short", day: "numeric", year: "numeric" });
    }

    buildTimelineAxis(start, end) {
        if (!start || !end) {
            return [];
        }
        const total = Math.max(end - start, 0);
        return [0, 0.5, 1].map((ratio) => this.formatMonth(new Date(start.getTime() + total * ratio)));
    }

    get dateRangeLabel() {
        return this.state.timeline.dateRange || this.t("All scheduled dates");
    }

    get quickMetrics() {
        return [
            { key: "projects", label: this.t("Projects"), value: this.state.counts.projects, icon: "fa-building-o", tone: "blue" },
            { key: "subProjects", label: this.t("Sub Projects"), value: this.state.counts.subProjects, icon: "fa-sitemap", tone: "teal" },
            { key: "workOrders", label: this.t("Work Orders"), value: this.state.counts.workOrders, icon: "fa-wrench", tone: "orange" },
            { key: "materialRequests", label: this.t("Material Requests"), value: this.state.counts.materialRequests, icon: "fa-clipboard", tone: "purple" },
            { key: "phases", label: this.t("Phases (WBS)"), value: this.state.counts.phases, icon: "fa-cubes", tone: "rose" },
            { key: "budgets", label: this.t("Budgets"), value: this.state.counts.budgets, icon: "fa-line-chart", tone: "navy" },
        ];
    }

    get portfolioMetrics() {
        return [
            { key: "projects", label: this.t("Active Projects"), value: this.state.counts.projects, icon: "fa-building-o", tone: "blue" },
            { key: "openWorkOrders", label: this.t("Open Work Orders"), value: this.state.counts.openWorkOrders, icon: "fa-wrench", tone: "green" },
            { key: "openMaterialRequests", label: this.t("Open Materials"), value: this.state.counts.openMaterialRequests, icon: "fa-clipboard", tone: "orange" },
            { key: "completedHandovers", label: this.t("Completed Handovers"), value: this.state.counts.completedHandovers, icon: "fa-check", tone: "teal" },
        ];
    }

    get completionLabel() {
        return `${this.state.counts.completion || 0}%`;
    }

    get stageMetrics() {
        return [
            { key: "planning", label: this.t("Planning"), value: this.state.counts.planning, icon: "fa-calendar-check-o", tone: "blue" },
            { key: "procurement", label: this.t("Procurement"), value: this.state.counts.procurement, icon: "fa-shopping-basket", tone: "orange" },
            { key: "construction", label: this.t("Construction"), value: this.state.counts.construction, icon: "fa-industry", tone: "green" },
            { key: "handover", label: this.t("Handover"), value: this.state.counts.handover, icon: "fa-check-square-o", tone: "navy" },
            { key: "done", label: this.t("Done"), value: this.state.counts.done, icon: "fa-check-circle-o", tone: "teal" },
        ];
    }

    get materialMetrics() {
        return this.state.materialStatuses.map((status) => ({
            ...status,
            key: `material:${status.key}`,
            tone: this.toneFromColor(status.color),
        }));
    }

    get transferMetrics() {
        return this.state.transferStatuses.map((status) => ({
            ...status,
            key: `transfer:${status.key}`,
            tone: this.toneFromColor(status.color),
        }));
    }

    toneFromColor(color) {
        const tones = {
            "#0ea5e9": "blue",
            "#14b8a6": "teal",
            "#f97316": "orange",
            "#f59e0b": "orange",
            "#ef4444": "rose",
            "#176b87": "blue",
            "#0f2742": "navy",
            "#22c55e": "green",
        };
        return tones[color] || "slate";
    }

    openModel(model, name, domain = [], context = {}) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name,
            res_model: model,
            views: [[false, "list"], [false, "form"]],
            domain,
            context,
            target: "current",
        });
    }

    onMetricClick(ev) {
        const key = ev.currentTarget.dataset.key;
        if (key) {
            this.openMetric(key);
        }
    }

    onStatusClick(ev) {
        const modelKey = ev.currentTarget.dataset.model;
        const state = ev.currentTarget.dataset.state;
        if (!modelKey || !state || state === "empty") {
            return;
        }
        const model = MODELS[modelKey];
        const field = modelKey === "subProjects" ? "stage" : "state";
        const titleMap = {
            subProjects: this.t("Sub Projects"),
            workOrders: this.t("Work Orders"),
            materialRequests: this.t("Material Requests"),
            internalTransfers: this.t("Transfers"),
        };
        this.openModel(model, titleMap[modelKey], [[field, "=", state]]);
    }

    openMetric(key) {
        const metricActions = {
            projects: () => this.openModel(MODELS.projects, this.t("Projects")),
            subProjects: () => this.openModel(MODELS.subProjects, this.t("Sub Projects")),
            workOrders: () => this.openModel(MODELS.workOrders, this.t("Work Orders")),
            openWorkOrders: () => this.openModel(MODELS.workOrders, this.t("Open Work Orders"), [["state", "!=", "completed"]]),
            materialRequests: () => this.openModel(MODELS.materialRequests, this.t("Material Requests")),
            openMaterialRequests: () => this.openModel(MODELS.materialRequests, this.t("Open Materials"), [["state", "!=", "done"]]),
            internalTransfers: () => this.openModel(MODELS.internalTransfers, this.t("Transfers")),
            phases: () => this.openModel(MODELS.phases, this.t("Phases (WBS)")),
            budgets: () => this.openModel(MODELS.budgets, this.t("Budgets")),
            completedHandovers: () => this.openModel(MODELS.subProjects, this.t("Completed Handovers"), [["stage", "=", "done"]]),
            completion: () => this.openModel(MODELS.subProjects, this.t("Sub Projects")),
            planning: () => this.openModel(MODELS.subProjects, this.t("Planning"), [["stage", "=", "planning"]]),
            procurement: () => this.openModel(MODELS.subProjects, this.t("Procurement"), [["stage", "=", "procurement"]]),
            construction: () => this.openModel(MODELS.subProjects, this.t("Construction"), [["stage", "=", "construction"]]),
            handover: () => this.openModel(MODELS.subProjects, this.t("Handover"), [["stage", "=", "handover"]]),
            done: () => this.openModel(MODELS.subProjects, this.t("Done"), [["stage", "=", "done"]]),
        };

        if (key.startsWith("material:")) {
            const state = key.replace("material:", "");
            if (state === "empty") {
                return;
            }
            return this.openModel(MODELS.materialRequests, this.t("Material Requests"), [["state", "=", state]]);
        }
        if (key.startsWith("transfer:")) {
            const state = key.replace("transfer:", "");
            if (state === "empty") {
                return;
            }
            return this.openModel(MODELS.internalTransfers, this.t("Transfers"), [["state", "=", state]]);
        }
        if (metricActions[key]) {
            return metricActions[key]();
        }
        return this.openModel(MODELS.projects, this.t("Projects"));
    }
}

registry.category("actions").add("tn_construction_dashboard.main", ConstructionDashboard);
