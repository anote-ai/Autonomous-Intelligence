import { Command } from "commander";
import chalk from "chalk";
import * as fs from "fs";
import * as path from "path";
import * as readline from "readline";
import { execSync } from "child_process";

interface StackInfo { language: string; framework: string; testCmd: string; buildCmd: string; lintCmd: string; }

function detectStack(cwd: string): StackInfo {
  const has = (f: string) => fs.existsSync(path.join(cwd, f));
  const read = (f: string): Record<string, unknown> => { try { return JSON.parse(fs.readFileSync(path.join(cwd, f), "utf8")); } catch { return {}; } };

  if (has("package.json")) {
    const pkg = read("package.json") as { scripts?: Record<string, string>; dependencies?: Record<string, string>; devDependencies?: Record<string, string> };
    const deps = { ...(pkg.dependencies ?? {}), ...(pkg.devDependencies ?? {}) };
    const scripts = pkg.scripts ?? {};
    const isTs = has("tsconfig.json");
    const language = isTs ? "TypeScript" : "JavaScript";
    let framework = "Node.js";
    if (deps["next"]) framework = "Next.js";
    else if (deps["react"]) framework = "React";
    else if (deps["vue"]) framework = "Vue";
    else if (deps["express"]) framework = "Express";
    else if (deps["@nestjs/core"]) framework = "NestJS";
    return { language, framework, testCmd: scripts["test"] ? "npm test" : "npm run test", buildCmd: scripts["build"] ? "npm run build" : "", lintCmd: scripts["lint"] ? "npm run lint" : deps["eslint"] ? "npx eslint ." : "" };
  }
  if (has("Cargo.toml")) return { language: "Rust", framework: "Cargo", testCmd: "cargo test", buildCmd: "cargo build", lintCmd: "cargo clippy" };
  if (has("pyproject.toml") || has("setup.py") || has("requirements.txt")) return { language: "Python", framework: has("pyproject.toml") ? "pyproject" : "pip", testCmd: "pytest", buildCmd: "", lintCmd: "ruff check ." };
  if (has("go.mod")) return { language: "Go", framework: "Go modules", testCmd: "go test ./...", buildCmd: "go build ./...", lintCmd: "golangci-lint run" };
  if (has("Gemfile")) return { language: "Ruby", framework: "Bundler", testCmd: "bundle exec rspec", buildCmd: "", lintCmd: "bundle exec rubocop" };
  return { language: "unknown", framework: "unknown", testCmd: "", buildCmd: "", lintCmd: "" };
}

function clawMdTemplate(cwd: string, stack: StackInfo): string {
  const cmds = [stack.testCmd, stack.lintCmd, stack.buildCmd].filter(Boolean);
  const verifyBlock = cmds.length ? cmds.map(c => `  ${c}`).join("\n") : "  # Add your test/lint/build commands here";
  return `# CLAW.md\n\nThis file provides guidance to Anote AI when working with code in this repository.\n\n## Project overview\n\n<!-- Describe what this project does -->\n\n## Stack\n\n${stack.language} · ${stack.framework}\n\n## Verification\n\nRun these before considering a change complete:\n\n${verifyBlock}\n\n## Working agreement\n\n- Read relevant files before making changes\n- Run the verification commands after modifying logic\n- Keep changes small and focused\n- Prefer editing existing files over creating new ones\n\n## Directory\n\n${cwd}\n`;
}

const makeDefaultConfig = (model: string, mode: string) => ({ model, permissionMode: mode, maxTurns: 20, compactAfterMessages: 40, hooks: { preToolUse: [], postToolUse: [] } });

async function prompt(rl: readline.Interface, question: string): Promise<string> {
  return new Promise((resolve) => rl.question(question, resolve));
}

export function initCommand(): Command {
  return new Command("init")
    .description("Scaffold .anote.json config and CLAW.md with auto-detected stack")
    .option("--yes", "accept all defaults without prompting")
    .action(async (opts) => {
      const cwd = process.cwd();
      const configPath = path.join(cwd, ".anote.json");
      const clawPath = path.join(cwd, "CLAW.md");

      console.log(chalk.bold.cyan("\n◆ Anote Init\n"));
      const stack = detectStack(cwd);
      if (stack.language !== "unknown") console.log(chalk.gray(`  Detected: ${stack.language} · ${stack.framework}\n`));

      let model = "claude-sonnet-4-6";
      let mode = "default";
      let addClaw = true;

      if (!opts.yes) {
        const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
        const modelInput = (await prompt(rl, chalk.gray("  Model [claude-sonnet-4-6 / gpt-4.1 / gemini-2.5-pro]: "))).trim();
        const modeInput = (await prompt(rl, chalk.gray("  Permission mode [default / acceptEdits / bypassPermissions]: "))).trim();

        if (!process.env.ANTHROPIC_API_KEY) {
          console.log(chalk.yellow("\n  ANTHROPIC_API_KEY is not set."));
          const keyInput = (await prompt(rl, chalk.gray("  Paste your API key (or press Enter to skip): "))).trim();
          if (keyInput) {
            const envPath = path.join(cwd, ".env");
            if (fs.existsSync(envPath)) {
              const envContent = fs.readFileSync(envPath, "utf8");
              if (!envContent.includes("ANTHROPIC_API_KEY")) { fs.appendFileSync(envPath, `\nANTHROPIC_API_KEY=${keyInput}\n`); console.log(chalk.green("  ✓ Added ANTHROPIC_API_KEY to .env")); }
            } else {
              console.log(chalk.cyan(`  Add this to your shell profile:\n  export ANTHROPIC_API_KEY=${keyInput}`));
            }
          }
        }

        const clawInput = (await prompt(rl, chalk.gray("  Create CLAW.md project memory file? [Y/n]: "))).trim().toLowerCase();
        addClaw = clawInput !== "n";
        rl.close();
        if (modelInput) model = modelInput;
        if (modeInput) mode = modeInput;
      } else {
        if (!process.env.ANTHROPIC_API_KEY) console.log(chalk.yellow("  Tip: set ANTHROPIC_API_KEY before running anote chat\n"));
      }

      if (addClaw) {
        if (fs.existsSync(clawPath)) console.log(chalk.yellow("  CLAW.md already exists, skipping."));
        else { fs.writeFileSync(clawPath, clawMdTemplate(cwd, stack), "utf8"); console.log(chalk.green("  ✓ Created CLAW.md")); }
      }

      if (fs.existsSync(configPath)) console.log(chalk.yellow("  .anote.json already exists — skipping."));
      else { fs.writeFileSync(configPath, JSON.stringify(makeDefaultConfig(model, mode), null, 2) + "\n", "utf8"); console.log(chalk.green("  ✓ Created .anote.json")); }

      console.log(chalk.bold(`\nNext steps:\n  ${chalk.cyan("export ANTHROPIC_API_KEY=sk-ant-...")}\n  ${chalk.white("anote chat")}        — start an AI pair programming session\n  ${chalk.white("anote doctor")}      — check your environment\n`));
    });
}

export function doctorCommand(): Command {
  return new Command("doctor")
    .description("Diagnose your Anote environment")
    .action(() => {
      console.log(chalk.bold.cyan("\n◆ Anote Doctor\n"));
      const cwd = process.cwd();
      const cmd = (c: string) => { try { return execSync(c, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim(); } catch { return ""; } };

      const checks = [
        { label: "Node.js ≥ 18", ok: (() => { const v = process.versions.node.split(".").map(Number); return v[0] >= 18; })(), detail: `Node.js ${process.versions.node}` },
        { label: "ANTHROPIC_API_KEY set", ok: !!process.env.ANTHROPIC_API_KEY, detail: process.env.ANTHROPIC_API_KEY ? `sk-ant-...${process.env.ANTHROPIC_API_KEY.slice(-4)}` : "not set" },
        { label: ".anote.json present", ok: fs.existsSync(path.join(cwd, ".anote.json")), detail: fs.existsSync(path.join(cwd, ".anote.json")) ? "found" : "run anote init" },
        { label: "CLAW.md present", ok: fs.existsSync(path.join(cwd, "CLAW.md")), detail: fs.existsSync(path.join(cwd, "CLAW.md")) ? "found" : "run anote init" },
        { label: "git installed", ok: !!cmd("git --version"), detail: cmd("git --version") || "not found" },
      ];

      for (const c of checks) {
        const icon = c.ok ? chalk.green("✓") : chalk.red("✗");
        console.log(`  ${icon}  ${c.ok ? chalk.white(c.label) : chalk.red(c.label)}`);
        console.log(chalk.gray(`       ${c.detail}`));
      }

      const failed = checks.filter(c => !c.ok);
      console.log("");
      if (failed.length === 0) console.log(chalk.green.bold("  All checks passed. You're good to go!\n"));
      else console.log(chalk.yellow(`  ${failed.length} issue(s) found. Fix the items above and run anote doctor again.\n`));
    });
}
