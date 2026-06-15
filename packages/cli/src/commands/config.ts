import { Command } from "commander";
import chalk from "chalk";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { loadConfig, type AnoteConfig } from "../config.js";

const GLOBAL_CONFIG_PATH = path.join(os.homedir(), ".anote", "config.json");

function readGlobalConfig(): AnoteConfig {
  if (!fs.existsSync(GLOBAL_CONFIG_PATH)) return {};
  try { return JSON.parse(fs.readFileSync(GLOBAL_CONFIG_PATH, "utf8")) as AnoteConfig; } catch { return {}; }
}

function writeGlobalConfig(cfg: AnoteConfig): void {
  const dir = path.dirname(GLOBAL_CONFIG_PATH);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(GLOBAL_CONFIG_PATH, JSON.stringify(cfg, null, 2) + "\n");
}

function formatValue(v: unknown): string {
  if (v === undefined || v === null) return chalk.gray("(not set)");
  if (typeof v === "string") return chalk.green(v);
  if (typeof v === "number") return chalk.yellow(String(v));
  if (typeof v === "boolean") return chalk.cyan(String(v));
  return chalk.white(JSON.stringify(v));
}

export function configCommand(): Command {
  const cmd = new Command("config").description("View or edit Anote configuration");

  cmd.command("list", { isDefault: true, hidden: true }).alias("ls").description("Show all configuration values").action(() => showAll());

  cmd.command("get <key>").description("Get a single config value").action((key: string) => {
    const cfg = readGlobalConfig();
    const local = loadConfig(process.cwd());
    const effective = { ...cfg, ...local };
    console.log(formatValue((effective as Record<string, unknown>)[key]));
  });

  cmd.command("set <key> <value>").description("Set a config value globally").action((key: string, rawValue: string) => {
    const cfg = readGlobalConfig();
    let value: unknown = rawValue;
    if (rawValue === "true") value = true;
    else if (rawValue === "false") value = false;
    else if (/^\d+$/.test(rawValue)) value = parseInt(rawValue, 10);
    (cfg as Record<string, unknown>)[key] = value;
    writeGlobalConfig(cfg);
    console.log(chalk.green("✓") + ` Set ${chalk.bold(key)} = ${formatValue(value)}` + chalk.gray(`  (${GLOBAL_CONFIG_PATH})`));
  });

  cmd.command("unset <key>").description("Remove a config value").action((key: string) => {
    const cfg = readGlobalConfig();
    if (!(key in cfg)) { console.log(chalk.yellow(`${key} is not set — nothing to do.`)); return; }
    delete (cfg as Record<string, unknown>)[key];
    writeGlobalConfig(cfg);
    console.log(chalk.green("✓") + ` Unset ${chalk.bold(key)}`);
  });

  cmd.command("path").description("Print the global config file path").action(() => console.log(GLOBAL_CONFIG_PATH));

  cmd.command("edit").description("Open the config file in $EDITOR").action(() => {
    const cfg = readGlobalConfig();
    if (!fs.existsSync(GLOBAL_CONFIG_PATH)) writeGlobalConfig(cfg);
    const editor = process.env.EDITOR ?? process.env.VISUAL ?? "vi";
    const { spawnSync } = require("child_process") as typeof import("child_process");
    const result = spawnSync(editor, [GLOBAL_CONFIG_PATH], { stdio: "inherit" });
    if (result.error) { console.error(chalk.red(`Could not open editor: ${result.error.message}`)); console.log(`Edit manually: ${GLOBAL_CONFIG_PATH}`); }
  });

  cmd.action(() => showAll());
  return cmd;
}

function showAll(): void {
  const globalCfg = readGlobalConfig();
  const localCfg = loadConfig(process.cwd());
  const KEYS: (keyof AnoteConfig)[] = ["model", "provider", "baseUrl", "permissionMode", "maxTurns", "compactAfterMessages"];
  console.log(chalk.bold("\nAnote Configuration\n"));
  console.log(chalk.gray(`  Global config:  ${GLOBAL_CONFIG_PATH}\n`));
  const effective: AnoteConfig = { ...globalCfg, ...localCfg };
  const COL = 28;
  for (const key of KEYS) {
    const val = (effective as Record<string, unknown>)[key];
    const isLocal = key in localCfg;
    const label = key.padEnd(COL);
    const source = isLocal ? chalk.gray(" (local)") : "";
    console.log(`  ${chalk.bold(label)}${formatValue(val)}${source}`);
  }
  console.log("");
  console.log(chalk.gray("  Run `anote config set <key> <value>` to change a value.\n"));
}
