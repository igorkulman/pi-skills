/**
 * review_findings_selector extension
 *
 * Registers a `review_findings_selector` tool the LLM calls after presenting
 * code-review findings. Shows an interactive checkbox UI so the user can pick
 * which findings to post as GitLab inline comments.
 *
 * Controls:
 *   ↑ / ↓   — move cursor
 *   Space   — toggle current finding
 *   a       — select / deselect all
 *   Enter   — confirm and post selected
 *   Esc     — cancel (post nothing)
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Key, Text, matchesKey, truncateToWidth } from "@earendil-works/pi-tui";
import { Type } from "typebox";

interface Finding {
	id: string;
	severity: string;
	file: string;
	title: string;
}

interface SelectionResult {
	selected: Finding[];
	cancelled: boolean;
	status: "selected" | "cancelled" | "needs_input" | "empty";
}

const FindingSchema = Type.Object({
	id: Type.String({ description: "Unique finding identifier, e.g. '1'" }),
	severity: Type.String({ description: "Severity label: Critical, High, Medium, Low, or Nit" }),
	file: Type.String({ description: "File path and optional line number, e.g. 'Foo.swift:42'" }),
	title: Type.String({ description: "One-line summary of the finding" }),
});

const Params = Type.Object({
	findings: Type.Array(FindingSchema, {
		description: "All findings from the review. Pass every finding so the user can pick which ones to post.",
	}),
});

const SelectionSchema = Type.Object({
	selected: Type.Array(FindingSchema),
	cancelled: Type.Boolean(),
	status: Type.Union([Type.Literal("selected"), Type.Literal("cancelled"), Type.Literal("needs_input"), Type.Literal("empty")]),
});

function selectionResult(text: string, details: SelectionResult, isError = false) {
	return { content: [{ type: "text" as const, text }], details, structuredContent: details, isError };
}

export default function reviewFindingsSelectorExtension(pi: ExtensionAPI) {
	pi.registerTool({
		name: "review_findings_selector",
		label: "Select Findings to Post",
		description:
			"Show an interactive checkbox UI for the user to select which code-review findings to post as GitLab inline comments. Call this immediately after presenting all review findings.",
		promptSnippet: "Ask which review findings to post to GitLab; no posting is approved until the user selects findings",
		exposure: "model-only",
		annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
		parameters: Params,
		outputSchema: SelectionSchema,

		async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
			const findings: Finding[] = params.findings;
			if (findings.length === 0) {
				return selectionResult("No findings were passed — nothing to select.", { selected: [], cancelled: false, status: "empty" });
			}
			if (new Set(findings.map((f) => f.id)).size !== findings.length || findings.some((f) =>
				!f.id.trim() || /[\s,]/.test(f.id) || ["all", "none", "cancel"].includes(f.id.toLowerCase()),
			)) {
				return selectionResult("Finding IDs must be unique, non-empty tokens without spaces or commas, and not all/none/cancel. No posting is approved.",
					{ selected: [], cancelled: false, status: "needs_input" }, true);
			}

			if (!ctx.hasUI) {
				return selectionResult("Interactive UI is unavailable. Ask the user which finding IDs they want to post. This is pending input, not cancellation or posting approval.",
					{ selected: [], cancelled: false, status: "needs_input" });
			}
			let result: SelectionResult;
			if (ctx.mode !== "tui") {
				const list = findings.map((f) => `${f.id}: [${f.severity}] ${f.title} (${f.file})`).join("\n");
				const answer = await ctx.ui.input(`Select findings to post to GitLab\n${list}`, "IDs separated by commas/spaces, all, none, or cancel");
				if (answer === undefined || answer.trim().toLowerCase() === "cancel") {
					result = { selected: [], cancelled: true, status: "cancelled" };
				} else {
					const value = answer.trim();
					const ids = value.toLowerCase() === "all" ? findings.map((f) => f.id)
						: !value || value.toLowerCase() === "none" ? [] : value.split(/[\s,]+/).filter(Boolean);
					const unknown = ids.filter((id) => !findings.some((f) => f.id === id));
					if (unknown.length > 0) {
						return selectionResult(`Unknown finding IDs: ${unknown.join(", ")}. Ask for a valid selection; no posting is approved.`,
							{ selected: [], cancelled: false, status: "needs_input" });
					}
					const selected = new Set(ids);
					result = { selected: findings.filter((f) => selected.has(f.id)), cancelled: false, status: "selected" };
				}
			} else {
				result = await ctx.ui.custom<SelectionResult>((tui, theme, _kb, done) => {
					let cursor = 0;
					// Start with every finding checked so the user just deselects unwanted ones.
					const checked = new Set<string>(findings.map((f) => f.id));
					let cachedLines: string[] | undefined;
					let cachedWidth = -1;

					function refresh() {
						cachedLines = undefined;
						tui.requestRender();
					}

					function severityColor(severity: string): "error" | "warning" | "muted" | "dim" {
						const s = severity.toLowerCase();
						if (s === "critical" || s === "high") return "error";
						if (s === "medium") return "warning";
						if (s === "low") return "muted";
						return "dim"; // nit / unknown
					}

					function render(width: number): string[] {
						if (cachedLines && cachedWidth === width) return cachedLines;
						const lines: string[] = [];
						const add = (s: string) => lines.push(truncateToWidth(s, width));

						// Header
						add(theme.fg("accent", "─".repeat(width)));
						add(theme.fg("accent", theme.bold(" Select findings to post to GitLab")));
						lines.push("");

						for (let i = 0; i < findings.length; i++) {
							const f = findings[i]!;
							const isCursor = i === cursor;
							const isChecked = checked.has(f.id);

							const cursorStr = isCursor ? theme.fg("accent", "> ") : "  ";
							const box = isChecked
								? theme.fg("success", "☑")
								: theme.fg("dim", "☐");
							const severityStr = theme.fg(severityColor(f.severity), `[${f.severity}]`);
							const titleStr = isCursor
								? theme.fg("text", f.title)
								: theme.fg("muted", f.title);

							add(`${cursorStr}${box} ${severityStr} ${titleStr}`);

							if (f.file) {
								add(`     ${theme.fg("dim", f.file)}`);
							}
						}

						// Footer hints
						lines.push("");
						const allChecked = checked.size === findings.length;
						add(
							theme.fg(
								"dim",
								`  ↑↓ navigate  •  space toggle  •  a ${allChecked ? "deselect all" : "select all"}  •  enter post  •  esc cancel`,
							),
						);
						add(theme.fg("accent", "─".repeat(width)));

						cachedLines = lines;
						cachedWidth = width;
						return lines;
					}

					function handleInput(data: string): void {
						// Navigate
						if (matchesKey(data, Key.up)) {
							cursor = Math.max(0, cursor - 1);
							refresh();
							return;
						}
						if (matchesKey(data, Key.down)) {
							cursor = Math.min(findings.length - 1, cursor + 1);
							refresh();
							return;
						}

						// Toggle current
						if (matchesKey(data, Key.space)) {
							const id = findings[cursor]?.id;
							if (id) {
								if (checked.has(id)) checked.delete(id);
								else checked.add(id);
								refresh();
							}
							return;
						}

						// Select / deselect all
						if (data === "a") {
							if (checked.size === findings.length) {
								checked.clear();
							} else {
								for (const f of findings) checked.add(f.id);
							}
							refresh();
							return;
						}

						// Confirm
						if (matchesKey(data, Key.enter)) {
							done({ selected: findings.filter((f) => checked.has(f.id)), cancelled: false, status: "selected" });
							return;
						}

						// Cancel
						if (matchesKey(data, Key.escape)) {
							done({ selected: [], cancelled: true, status: "cancelled" });
						}
					}

					return {
						render,
						invalidate: () => {
							cachedLines = undefined;
						},
						handleInput,
					};
				}) ?? { selected: [], cancelled: true, status: "cancelled" };
			}

			// User cancelled
			if (result.cancelled) {
				return selectionResult("User cancelled. No findings will be posted.", result);
			}

			// Nothing selected
			if (result.selected.length === 0) {
				return selectionResult("User selected no findings. Nothing will be posted.", result);
			}

			// Build summary for the LLM
			const summary = result.selected
				.map((f) => `- [${f.severity}] ${f.title}  (${f.file})`)
				.join("\n");

			return selectionResult(`User selected ${result.selected.length} finding(s) to post:\n${summary}\n\nPost only these as GitLab inline comments, following the review posting workflow.`, result);
		},

		renderCall(args, theme, _context) {
			const count = (args.findings as Finding[] | undefined)?.length ?? 0;
			let line = theme.fg("toolTitle", theme.bold("review_findings_selector "));
			line += theme.fg("muted", `${count} finding${count !== 1 ? "s" : ""}`);
			return new Text(line, 0, 0);
		},

		renderResult(result, _options, theme, _context) {
			const details = result.details as SelectionResult | undefined;

			if (!details) {
				const first = result.content[0];
				return new Text(first?.type === "text" ? first.text : "", 0, 0);
			}

			if (details.status === "needs_input") {
				return new Text(theme.fg("warning", "Selection pending — ask the user; no posting approved"), 0, 0);
			}

			if (details.cancelled) {
				return new Text(theme.fg("warning", "Cancelled — nothing will be posted"), 0, 0);
			}

			if (details.selected.length === 0) {
				return new Text(theme.fg("dim", "No findings selected — nothing will be posted"), 0, 0);
			}

			const lines = details.selected.map(
				(f) =>
					`${theme.fg("success", "✓ ")}${theme.fg("accent", `[${f.severity}]`)} ${theme.fg("text", f.title)}`,
			);
			return new Text(lines.join("\n"), 0, 0);
		},
	});
}
