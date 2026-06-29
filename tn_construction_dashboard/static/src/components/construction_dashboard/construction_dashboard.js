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
    "Clear": "مسح",
    "Reset filters": "مسح الفلاتر",
    "Project": "المشروع",
    "Sub Project": "المشروع الفرعي",
    "Stage": "المرحلة",
    "All projects": "كل المشاريع",
    "All sub projects": "كل المشاريع الفرعية",
    "All stages": "كل المراحل",
    "All dates": "كل التواريخ",
    "Today": "اليوم",
    "This week": "هذا الأسبوع",
    "This month": "هذا الشهر",
    "Next 30 days": "الـ 30 يوم القادمة",
    "Custom": "مخصص",
    "From": "من",
    "To": "إلى",
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
            refreshing: false,
            counts: {},
            subProjectStages: [],
            workOrderStatuses: [],
            materialStatuses: [],
            transferStatuses: [],
            timeline: { axis: [] },
            filterOptions: {
                projects: [],
                subProjects: [],
            },
            filterPanelOpen: false,
            datePanelOpen: false,
            filters: {
                projectId: false,
                subProjectId: false,
                stage: "",
                datePreset: "all",
                dateFrom: "",
                dateTo: "",
            },
        });

        onWillStart(async () => {
            await this.loadFilterOptions();
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
            clear: this.t("Clear"),
            resetFilters: this.t("Reset filters"),
            project: this.t("Project"),
            subProject: this.t("Sub Project"),
            stage: this.t("Stage"),
            allProjects: this.t("All projects"),
            allSubProjects: this.t("All sub projects"),
            allStages: this.t("All stages"),
            from: this.t("From"),
            to: this.t("To"),
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

    get datePresets() {
        return [
            { key: "all", label: this.t("All dates") },
            { key: "today", label: this.t("Today") },
            { key: "this_week", label: this.t("This week") },
            { key: "this_month", label: this.t("This month") },
            { key: "next_30", label: this.t("Next 30 days") },
            { key: "custom", label: this.t("Custom") },
        ];
    }

    get filteredSubProjects() {
        const projectId = this.state.filters.projectId;
        if (!projectId) {
            return this.state.filterOptions.subProjects;
        }
        return this.state.filterOptions.subProjects.filter((subProject) => {
            const project = subProject.project_id;
            return Array.isArray(project) && project[0] === projectId;
        });
    }

    get stageOptions() {
        return Object.entries(this.subProjectStageLabels).map(([key, label]) => ({ key, label }));
    }

    get activeFilterCount() {
        const filters = this.state.filters;
        return [
            filters.projectId,
            filters.subProjectId,
            filters.stage,
            filters.dateFrom || filters.dateTo,
        ].filter(Boolean).length;
    }

    get activeFilterChips() {
        const filters = this.state.filters;
        const chips = [];
        if (filters.projectId) {
            chips.push({
                key: "project",
                label: this.findOptionLabel(this.state.filterOptions.projects, filters.projectId),
            });
        }
        if (filters.subProjectId) {
            chips.push({
                key: "subProject",
                label: this.findOptionLabel(this.state.filterOptions.subProjects, filters.subProjectId),
            });
        }
        if (filters.stage) {
            chips.push({ key: "stage", label: this.subProjectStageLabels[filters.stage] || filters.stage });
        }
        if (filters.dateFrom || filters.dateTo) {
            chips.push({ key: "date", label: this.dateRangeLabel });
        }
        return chips;
    }

    findOptionLabel(options, id) {
        const option = options.find((item) => item.id === id);
        return option ? option.display_name || option.name : "";
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

    async loadFilterOptions() {
        const [projects, subProjects] = await Promise.all([
            this.safeSearchRead(MODELS.projects, [], ["display_name"], { order: "name asc", limit: 500 }),
            this.safeSearchRead(
                MODELS.subProjects,
                [],
                ["display_name", "project_id", "stage"],
                { order: "project_id, sequence, name", limit: 1000 }
            ),
        ]);
        this.state.filterOptions = { projects, subProjects };
    }

    async loadDashboard() {
        const requestId = (this._dashboardRequestId || 0) + 1;
        this._dashboardRequestId = requestId;
        this.state.refreshing = true;

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
            this.safeCount(MODELS.projects, this.baseDomain("projects")),
            this.safeCount(MODELS.subProjects, this.baseDomain("subProjects")),
            this.safeCount(MODELS.budgets, this.baseDomain("budgets")),
            this.safeCount(MODELS.phases, this.baseDomain("phases")),
            this.safeCount(MODELS.workOrders, this.baseDomain("workOrders")),
            this.safeCount(MODELS.workOrders, this.domainWith("workOrders", [["state", "!=", "completed"]])),
            this.safeCount(MODELS.materialRequests, this.baseDomain("materialRequests")),
            this.safeCount(MODELS.materialRequests, this.domainWith("materialRequests", [["state", "!=", "done"]])),
            this.safeCount(MODELS.internalTransfers, this.baseDomain("internalTransfers")),
            this.safeCount(MODELS.internalTransfers, this.domainWith("internalTransfers", [["state", "in", ["draft", "in_progress"]]])),
            this.safeCount(MODELS.subProjects, this.domainWith("subProjects", [["stage", "=", "done"]])),
            this.safeReadGroup(MODELS.subProjects, this.baseDomain("subProjects"), ["stage"], ["stage"]),
            this.safeReadGroup(MODELS.workOrders, this.baseDomain("workOrders"), ["state"], ["state"]),
            this.safeReadGroup(MODELS.materialRequests, this.baseDomain("materialRequests"), ["state"], ["state"]),
            this.safeReadGroup(MODELS.internalTransfers, this.baseDomain("internalTransfers"), ["state"], ["state"]),
            this.safeSearchRead(
                MODELS.subProjects,
                this.baseDomain("subProjects"),
                ["schedule_start_date", "schedule_end_date", "progress"]
            ),
        ]);

        if (requestId !== this._dashboardRequestId) {
            return;
        }

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
        this.state.refreshing = false;
    }

    baseDomain(modelKey) {
        const filters = this.state.filters;
        const domain = [];

        if (filters.projectId) {
            if (modelKey === "projects") {
                domain.push(["id", "=", filters.projectId]);
            } else {
                domain.push(["project_id", "=", filters.projectId]);
            }
        }

        if (filters.subProjectId) {
            if (modelKey === "projects") {
                domain.push(["construction_sub_project_ids", "in", [filters.subProjectId]]);
            } else if (modelKey === "subProjects") {
                domain.push(["id", "=", filters.subProjectId]);
            } else {
                domain.push(["sub_project_id", "=", filters.subProjectId]);
            }
        }

        if (filters.stage) {
            if (modelKey === "projects") {
                domain.push(["construction_sub_project_ids.stage", "=", filters.stage]);
            } else if (modelKey === "subProjects") {
                domain.push(["stage", "=", filters.stage]);
            } else {
                domain.push(["sub_project_id.stage", "=", filters.stage]);
            }
        }

        return domain.concat(this.dateDomain(modelKey));
    }

    domainWith(modelKey, extraDomain = []) {
        return this.baseDomain(modelKey).concat(extraDomain);
    }

    dateDomain(modelKey) {
        const filters = this.state.filters;
        const from = filters.dateFrom;
        const to = filters.dateTo;
        if (!from && !to) {
            return [];
        }

        const fieldMap = {
            projects: ["date_start", "date"],
            subProjects: ["schedule_start_date", "schedule_end_date"],
            budgets: ["start_date", "end_date"],
            phases: ["start_date", "end_date"],
            workOrders: ["start_date", "end_date"],
            materialRequests: ["date"],
            internalTransfers: ["date"],
        };
        const fields = fieldMap[modelKey];
        if (!fields) {
            return [];
        }
        if (fields.length === 1) {
            return [
                ...(from ? [[fields[0], ">=", `${from} 00:00:00`]] : []),
                ...(to ? [[fields[0], "<=", `${to} 23:59:59`]] : []),
            ];
        }
        return [
            ...(from ? [[fields[1], ">=", from]] : []),
            ...(to ? [[fields[0], "<=", to]] : []),
        ];
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
        const filters = this.state.filters;
        if (filters.dateFrom && filters.dateTo) {
            return `${this.formatDateText(filters.dateFrom)} - ${this.formatDateText(filters.dateTo)}`;
        }
        if (filters.dateFrom) {
            return `${this.t("From")} ${this.formatDateText(filters.dateFrom)}`;
        }
        if (filters.dateTo) {
            return `${this.t("To")} ${this.formatDateText(filters.dateTo)}`;
        }
        return this.t("All scheduled dates");
    }

    formatDateText(value) {
        const parsed = this.parseDate(value);
        return parsed ? this.formatFullDate(parsed) : value;
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
        this.openModel(model, titleMap[modelKey], this.domainWith(modelKey, [[field, "=", state]]));
    }

    async toggleDatePanel() {
        this.state.datePanelOpen = !this.state.datePanelOpen;
        this.state.filterPanelOpen = false;
    }

    async toggleFilterPanel() {
        this.state.filterPanelOpen = !this.state.filterPanelOpen;
        this.state.datePanelOpen = false;
    }

    async onProjectChange(ev) {
        const projectId = this.parseId(ev.target.value);
        this.state.filters.projectId = projectId;
        if (
            this.state.filters.subProjectId &&
            !this.filteredSubProjects.some((subProject) => subProject.id === this.state.filters.subProjectId)
        ) {
            this.state.filters.subProjectId = false;
        }
        await this.loadDashboard();
    }

    async onSubProjectChange(ev) {
        const subProjectId = this.parseId(ev.target.value);
        this.state.filters.subProjectId = subProjectId;
        if (subProjectId && !this.state.filters.projectId) {
            const subProject = this.state.filterOptions.subProjects.find((item) => item.id === subProjectId);
            if (subProject && Array.isArray(subProject.project_id)) {
                this.state.filters.projectId = subProject.project_id[0];
            }
        }
        await this.loadDashboard();
    }

    async onStageChange(ev) {
        this.state.filters.stage = ev.target.value || "";
        await this.loadDashboard();
    }

    async onDatePresetClick(ev) {
        const preset = ev.currentTarget.dataset.preset;
        this.applyDatePreset(preset);
        await this.loadDashboard();
    }

    async onDateFromChange(ev) {
        this.state.filters.datePreset = "custom";
        this.state.filters.dateFrom = ev.target.value || "";
        this.normalizeDateRange();
        await this.loadDashboard();
    }

    async onDateToChange(ev) {
        this.state.filters.datePreset = "custom";
        this.state.filters.dateTo = ev.target.value || "";
        this.normalizeDateRange();
        await this.loadDashboard();
    }

    async onRemoveFilter(ev) {
        const filter = ev.currentTarget.dataset.filter;
        if (filter === "project") {
            this.state.filters.projectId = false;
            this.state.filters.subProjectId = false;
        } else if (filter === "subProject") {
            this.state.filters.subProjectId = false;
        } else if (filter === "stage") {
            this.state.filters.stage = "";
        } else if (filter === "date") {
            this.state.filters.datePreset = "all";
            this.state.filters.dateFrom = "";
            this.state.filters.dateTo = "";
        }
        await this.loadDashboard();
    }

    async resetFilters() {
        Object.assign(this.state.filters, {
            projectId: false,
            subProjectId: false,
            stage: "",
            datePreset: "all",
            dateFrom: "",
            dateTo: "",
        });
        await this.loadDashboard();
    }

    parseId(value) {
        const id = parseInt(value, 10);
        return Number.isFinite(id) ? id : false;
    }

    applyDatePreset(preset) {
        const today = new Date();
        let start = null;
        let end = null;

        if (preset === "today") {
            start = today;
            end = today;
        } else if (preset === "this_week") {
            start = new Date(today);
            const day = start.getDay() || 7;
            start.setDate(start.getDate() - day + 1);
            end = new Date(start);
            end.setDate(start.getDate() + 6);
        } else if (preset === "this_month") {
            start = new Date(today.getFullYear(), today.getMonth(), 1);
            end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        } else if (preset === "next_30") {
            start = today;
            end = new Date(today);
            end.setDate(today.getDate() + 30);
        }

        this.state.filters.datePreset = preset || "all";
        this.state.filters.dateFrom = start ? this.toISODate(start) : "";
        this.state.filters.dateTo = end ? this.toISODate(end) : "";
    }

    normalizeDateRange() {
        const filters = this.state.filters;
        if (filters.dateFrom && filters.dateTo && filters.dateFrom > filters.dateTo) {
            const from = filters.dateFrom;
            filters.dateFrom = filters.dateTo;
            filters.dateTo = from;
        }
    }

    toISODate(value) {
        const year = value.getFullYear();
        const month = `${value.getMonth() + 1}`.padStart(2, "0");
        const day = `${value.getDate()}`.padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    openMetric(key) {
        const metricActions = {
            projects: () => this.openModel(MODELS.projects, this.t("Projects"), this.baseDomain("projects")),
            subProjects: () => this.openModel(MODELS.subProjects, this.t("Sub Projects"), this.baseDomain("subProjects")),
            workOrders: () => this.openModel(MODELS.workOrders, this.t("Work Orders"), this.baseDomain("workOrders")),
            openWorkOrders: () => this.openModel(MODELS.workOrders, this.t("Open Work Orders"), this.domainWith("workOrders", [["state", "!=", "completed"]])),
            materialRequests: () => this.openModel(MODELS.materialRequests, this.t("Material Requests"), this.baseDomain("materialRequests")),
            openMaterialRequests: () => this.openModel(MODELS.materialRequests, this.t("Open Materials"), this.domainWith("materialRequests", [["state", "!=", "done"]])),
            internalTransfers: () => this.openModel(MODELS.internalTransfers, this.t("Transfers"), this.baseDomain("internalTransfers")),
            phases: () => this.openModel(MODELS.phases, this.t("Phases (WBS)"), this.baseDomain("phases")),
            budgets: () => this.openModel(MODELS.budgets, this.t("Budgets"), this.baseDomain("budgets")),
            completedHandovers: () => this.openModel(MODELS.subProjects, this.t("Completed Handovers"), this.domainWith("subProjects", [["stage", "=", "done"]])),
            completion: () => this.openModel(MODELS.subProjects, this.t("Sub Projects"), this.baseDomain("subProjects")),
            planning: () => this.openModel(MODELS.subProjects, this.t("Planning"), this.domainWith("subProjects", [["stage", "=", "planning"]])),
            procurement: () => this.openModel(MODELS.subProjects, this.t("Procurement"), this.domainWith("subProjects", [["stage", "=", "procurement"]])),
            construction: () => this.openModel(MODELS.subProjects, this.t("Construction"), this.domainWith("subProjects", [["stage", "=", "construction"]])),
            handover: () => this.openModel(MODELS.subProjects, this.t("Handover"), this.domainWith("subProjects", [["stage", "=", "handover"]])),
            done: () => this.openModel(MODELS.subProjects, this.t("Done"), this.domainWith("subProjects", [["stage", "=", "done"]])),
        };

        if (key.startsWith("material:")) {
            const state = key.replace("material:", "");
            if (state === "empty") {
                return;
            }
            return this.openModel(MODELS.materialRequests, this.t("Material Requests"), this.domainWith("materialRequests", [["state", "=", state]]));
        }
        if (key.startsWith("transfer:")) {
            const state = key.replace("transfer:", "");
            if (state === "empty") {
                return;
            }
            return this.openModel(MODELS.internalTransfers, this.t("Transfers"), this.domainWith("internalTransfers", [["state", "=", state]]));
        }
        if (metricActions[key]) {
            return metricActions[key]();
        }
        return this.openModel(MODELS.projects, this.t("Projects"), this.baseDomain("projects"));
    }
}

registry.category("actions").add("tn_construction_dashboard.main", ConstructionDashboard);
