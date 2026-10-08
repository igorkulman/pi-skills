import type { Message, Usage } from "@earendil-works/pi-ai";
import type { SlashCommandInfo } from "@earendil-works/pi-coding-agent";

const PROVIDER_PACKAGES = ["npm:pi-multi-pass", "npm:@gotgenes/pi-anthropic-auth"];

/** Inherit only provider packages that are actually loaded in the parent. */
export function getProviderExtensions(commands: readonly SlashCommandInfo[]): string[] {
	return [...new Set(commands
		.filter((command) => command.source === "extension" && PROVIDER_PACKAGES.some((source) =>
			command.sourceInfo.source === source || command.sourceInfo.source.startsWith(`${source}@`),
		))
		.map((command) => command.sourceInfo.path))];
}

/** Include tool-owned usage as well as model usage, without counting partial updates. */
export function sumUsage(messages: readonly Message[]): Usage {
	const total: Usage = {
		input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0,
		cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
	};
	for (const message of messages) {
		if (message.role !== "assistant" && message.role !== "toolResult") continue;
		const usage = message.usage;
		if (!usage) continue;
		for (const key of ["input", "output", "cacheRead", "cacheWrite", "totalTokens"] as const) {
			total[key] += usage[key] || 0;
		}
		for (const key of ["cacheWrite1h", "reasoning"] as const) {
			if (usage[key] !== undefined) total[key] = (total[key] ?? 0) + usage[key];
		}
		for (const key of ["input", "output", "cacheRead", "cacheWrite", "total"] as const) {
			total.cost[key] += usage.cost?.[key] || 0;
		}
	}
	return total;
}
