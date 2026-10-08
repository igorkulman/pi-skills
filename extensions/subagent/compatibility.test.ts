import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { createRequire } from "node:module";
import { PassThrough } from "node:stream";
import { after, before, mock, test } from "node:test";
import { fileURLToPath } from "node:url";
import { getProviderExtensions, sumUsage } from "./compatibility.ts";

const source = (name: string, pkg: string, file: string) => ({
	name, source: "extension" as const,
	sourceInfo: { source: pkg, path: file, scope: "user" as const, origin: "package" as const },
});
const providerCommands = [
	source("subs", "npm:pi-multi-pass", "/providers/multi-pass.ts"),
	source("pool", "npm:pi-multi-pass", "/providers/multi-pass.ts"),
	source("anthropic-auth:status", "npm:@gotgenes/pi-anthropic-auth@3.4.2", "/providers/auth.ts"),
	source("xcode", "npm:pi-xcode-mcp", "/tools/xcode.ts"),
];
const usage = { input: 10, output: 2, cacheRead: 3, cacheWrite: 4, cacheWrite1h: 1, reasoning: 1,
	totalTokens: 19, cost: { input: 0.1, output: 0.2, cacheRead: 0.3, cacheWrite: 0.4, total: 1 } };
const assistant = (text = "OK", stopReason = "stop") => ({
	role: "assistant", content: [{ type: "text", text }], api: "openai-codex-responses",
	provider: "openai-codex-2", model: "test-model", usage, stopReason, timestamp: 1,
	...(stopReason === "error" ? { errorMessage: "Provider failed" } : {}),
});

test("only active provider package sources are inherited, once", () => {
	assert.deepEqual(getProviderExtensions(providerCommands), ["/providers/multi-pass.ts", "/providers/auth.ts"]);
	assert.deepEqual(getProviderExtensions([]), []);
	assert.deepEqual(getProviderExtensions([source("subs", "npm:pi-multi-pass-untrusted", "/bad.ts")]), []);
});

test("usage includes completed assistant and tool messages, with all cost fields", () => {
	const total = sumUsage([
		assistant(), { role: "toolResult", usage }, { role: "user", usage }, { role: "toolResult" },
	] as any);
	assert.deepEqual(total, {
		input: 20, output: 4, cacheRead: 6, cacheWrite: 8, totalTokens: 38, cacheWrite1h: 2, reasoning: 2,
		cost: { input: 0.2, output: 0.4, cacheRead: 0.6, cacheWrite: 0.8, total: 2 },
	});
	assert.equal(sumUsage([]).totalTokens, 0);
});

// Use Pi's own installed dependencies, without creating a package installation in this repository.
const agentDir = process.env.PI_CODING_AGENT_DIR ?? path.join(os.homedir(), ".pi", "agent");
const nodeModules = process.env.PI_NODE_MODULES ?? path.join(agentDir, "install", "releases",
	fs.readFileSync(path.join(agentDir, "install", "current-version"), "utf8").trim(), "node_modules");
const requirePi = createRequire(path.join(nodeModules, "package.json"));
const { createJiti } = requirePi("jiti");
const alias = Object.fromEntries(["pi-ai", "pi-agent-core", "pi-coding-agent", "pi-tui"].map((name) => [
	`@earendil-works/${name}`, path.join(nodeModules, "@earendil-works", name, "dist", name === "pi-ai" ? "compat.js" : "index.js"),
]));
alias.typebox = requirePi.resolve("typebox");
const jiti = createJiti(import.meta.url, { moduleCache: false, alias });
let discoverAgents: any;
let tool: any;
let tempDir: string;
let calls: { args: string[]; cwd: string }[];
let failNext = false;
let abortNext = false;
let controller: AbortController | undefined;
let previousAgentDir: string | undefined;

before(async () => {
	previousAgentDir = process.env.PI_CODING_AGENT_DIR;
	tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "pi-subagent-test-"));
	process.env.PI_CODING_AGENT_DIR = tempDir;
	fs.mkdirSync(path.join(tempDir, "agents"));
	fs.mkdirSync(path.join(tempDir, ".pi", "agents"), { recursive: true });
	fs.writeFileSync(path.join(tempDir, "agents", "test.md"), "---\nname: test\ndescription: Test agent\ntools: read, bash\n---\nRead-only test agent.");
	fs.writeFileSync(path.join(tempDir, "agents", "pinned.md"), "---\nname: pinned\ndescription: Pinned model\nmodel: openai-codex/test-model\nproviderExtensions:\n  - ../provider.ts\n---\nPinned agent.");
	fs.writeFileSync(path.join(tempDir, ".pi", "agents", "project.md"), "---\nname: project\ndescription: Project agent\n---\nProject prompt.");
	mock.method(requirePi("node:child_process"), "spawn", (_command: string, args: string[], options: any) => {
		calls.push({ args, cwd: options.cwd });
		const proc: any = new EventEmitter();
		proc.stdout = new PassThrough();
		proc.stderr = new PassThrough();
		proc.kill = () => { proc.killed = true; return true; };
		const failed = failNext;
		const aborted = abortNext;
		failNext = false;
		abortNext = false;
		queueMicrotask(() => {
			proc.stdout.write(`${JSON.stringify({ type: "message_end", message: assistant("OK", failed ? "error" : "stop") })}\n`);
			if (aborted) controller?.abort();
			proc.stdout.end();
			proc.emit("close", failed ? 1 : 0);
		});
		return proc;
	});
	const extension = await jiti.import(fileURLToPath(new URL("./index.ts", import.meta.url)), { default: true });
	({ discoverAgents } = await jiti.import(fileURLToPath(new URL("./agents.ts", import.meta.url))));
	extension({ registerTool: (value: any) => { tool = value; }, getCommands: () => providerCommands });
});
after(() => {
	mock.restoreAll();
	if (previousAgentDir === undefined) delete process.env.PI_CODING_AGENT_DIR;
	else process.env.PI_CODING_AGENT_DIR = previousAgentDir;
	fs.rmSync(tempDir, { recursive: true, force: true });
});
const run = async (params: any, updates?: any[], context?: any) => {
	calls = [];
	return tool.execute("test", params, controller?.signal, updates ? (value: any) => updates.push(value) : undefined, {
		cwd: tempDir, model: { provider: "openai-codex-2", id: "test-model" }, thinkingLevel: "high", hasUI: false,
		...context,
	});
};

test("single dispatch inherits secondary provider and thinking, but not MCP/workflow tools", async () => {
	const updates: any[] = [];
	const result = await run({ agent: "test", task: "Inspect", cwd: tempDir }, updates);
	const args = calls[0].args;
	assert.equal(args[args.indexOf("--model") + 1], "openai-codex-2/test-model");
	assert.equal(args[args.indexOf("--thinking") + 1], "high");
	assert.equal(args[args.indexOf("--tools") + 1], "read,bash");
	for (const flag of ["--no-session", "--no-extensions", "--no-mcp", "--no-skills", "--no-prompt-templates", "--no-themes"]) assert.ok(args.includes(flag));
	assert.deepEqual(args.filter((_, i) => args[i - 1] === "--extension"), ["/providers/multi-pass.ts", "/providers/auth.ts"]);
	assert.equal(result.usage.totalTokens, 19);
	assert.equal(result.usage.cost.total, 1);
	assert.ok(updates.length > 0);
	assert.ok(updates.every((update) => update.usage === undefined));
});

test("pinned models, tool-free agents, and explicit provider file paths", async () => {
	const result = await run({ agent: "pinned", task: "Inspect" });
	const args = calls[0].args;
	assert.equal(args[args.indexOf("--model") + 1], "openai-codex/test-model");
	assert.ok(!args.includes("--thinking"));
	assert.ok(args.includes("--no-tools"));
	assert.ok(args.includes(path.join(tempDir, "provider.ts")));
	assert.equal(result.usage.cost.total, 1);
	assert.ok(discoverAgents(tempDir, "user").agents.every((agent: any) => agent.source === "user"));
});

test("parallel totals and stopped-chain totals include failed children", async () => {
	let result = await run({ tasks: [{ agent: "test", task: "A" }, { agent: "test", task: "B" }] });
	assert.equal(result.usage.totalTokens, 38);
	assert.equal(result.usage.cost.total, 2);
	failNext = true;
	result = await run({ tasks: [{ agent: "test", task: "A" }, { agent: "test", task: "B" }] });
	assert.equal(result.isError, true);
	assert.equal(result.usage.cost.total, 2);
	failNext = true;
	result = await run({ chain: [{ agent: "test", task: "A" }, { agent: "test", task: "B {previous}" }] });
	assert.equal(calls.length, 1);
	assert.equal(result.isError, true);
	assert.equal(result.usage.cost.total, 1);
});

test("successful chains interpolate previous output and do not double-count updates", async () => {
	const updates: any[] = [];
	const result = await run({ chain: [{ agent: "test", task: "A" }, { agent: "test", task: "B {previous}" }] }, updates);
	assert.ok(calls[1].args.includes("Task: B OK"));
	assert.equal(result.usage.cost.total, 2);
	assert.ok(updates.every((update) => update.usage === undefined));
});

test("failed and aborted single runs retain spent usage", async () => {
	failNext = true;
	let result = await run({ agent: "test", task: "A" });
	assert.equal(result.isError, true);
	assert.equal(result.usage.cost.total, 1);
	controller = new AbortController();
	abortNext = true;
	result = await run({ agent: "test", task: "A" });
	assert.equal(result.isError, true);
	assert.equal(result.details.results[0].stopReason, "aborted");
	assert.equal(result.usage.cost.total, 1);
	controller = undefined;
});

test("project agent approval still prevents execution", async () => {
	const result = await run({ agent: "project", task: "A", agentScope: "both" }, undefined, {
		hasUI: true, ui: { confirm: async () => false },
	});
	assert.equal(calls.length, 0);
	assert.match(result.content[0].text, /not approved/);
});
