import { Command } from "commander";
import chalk from "chalk";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { loadConfig, type AnoteConfig, type McpServerConfig } from "../config.js";

const GLOBAL_CONFIG_PATH = path.join(os.homedir(), ".anote", "config.json");

function readGlobalConfig(): AnoteConfig {
  if (!fs.existsSync(GLOBAL_CONFIG_PATH)) return {};
  try {
    return JSON.parse(fs.readFileSync(GLOBAL_CONFIG_PATH, "utf8")) as AnoteConfig;
  } catch {
    return {};
  }
}

function writeGlobalConfig(cfg: AnoteConfig): void {
  const dir = path.dirname(GLOBAL_CONFIG_PATH);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(GLOBAL_CONFIG_PATH, JSON.stringify(cfg, null, 2) + "\n");
}

function describeServer(cfg: McpServerConfig): string {
  if ("command" in cfg) {
    return chalk.gray(`stdio: ${cfg.command}${cfg.args?.length ? " " + cfg.args.join(" ") : ""}`);
  }
  return chalk.gray(`${cfg.type}: ${cfg.url}`);
}

export function mcpCommand(): Command {
  const cmd = new Command("mcp").description("Manage MCP (Model Context Protocol) servers");

  cmd
    .command("list", { isDefault: true })
    .alias("ls")
    .description("List configured MCP servers")
    .action(() => {
      const servers = loadConfig(process.cwd()).mcpServers ?? {};
      const names = Object.keys(servers);
      if (!names.length) {
        console.log(
          chalk.gray("\nNo MCP servers configured.") +
            `\n  Add one:  ${chalk.cyan("anote mcp add <name> -- <command> [args…]")}\n`
        );
        return;
      }
      console.log(chalk.bold("\nMCP servers\n"));
      for (const name of names) {
        console.log(`  ${chalk.green(name.padEnd(22))} ${describeServer(servers[name])}`);
      }
      console.log("");
    });

  cmd
    .command("add <name> [args...]")
    .description("Add a stdio MCP server to global config (command after --)")
    .action((name: string, args: string[]) => {
      const parts = args[0] === "--" ? args.slice(1) : args;
      if (!parts.length) {
        console.error(
          chalk.red("✗ Provide the server command, e.g.\n  ") +
            chalk.cyan("anote mcp add github -- npx -y @modelcontextprotocol/server-github")
        );
        process.exitCode = 1;
        return;
      }
      const [command, ...rest] = parts;
      const cfg = readGlobalConfig();
      cfg.mcpServers = cfg.mcpServers ?? {};
      cfg.mcpServers[name] = { command, ...(rest.length ? { args: rest } : {}) };
      writeGlobalConfig(cfg);
      console.log(
        chalk.green("✓") +
          ` Added MCP server ${chalk.bold(name)}  ${describeServer(cfg.mcpServers[name])}` +
          chalk.gray(`  (${GLOBAL_CONFIG_PATH})`)
      );
    });

  cmd
    .command("remove <name>")
    .alias("rm")
    .description("Remove an MCP server from global config")
    .action((name: string) => {
      const cfg = readGlobalConfig();
      if (!cfg.mcpServers || !(name in cfg.mcpServers)) {
        console.log(chalk.yellow(`${name} is not configured — nothing to do.`));
        return;
      }
      delete cfg.mcpServers[name];
      writeGlobalConfig(cfg);
      console.log(chalk.green("✓") + ` Removed MCP server ${chalk.bold(name)}`);
    });

  return cmd;
}
