import { Command } from "commander";
import chalk from "chalk";
import * as fs from "fs";
import * as path from "path";
import { execSync } from "child_process";

interface Check {
  name: string;
  pass: boolean;
  message: string;
}

function checkCommand(cmd: string): boolean {
  try {
    execSync(`which ${cmd}`, { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

export function doctorCommand(): Command {
  return new Command("doctor")
    .alias("dr")
    .description("Check your environment for required tools and configuration")
    .option("-d, --dir <path>", "project directory to inspect", process.cwd())
    .action((opts) => {
      const cwd = path.resolve(opts.dir as string);
      const checks: Check[] = [];

      // API key
      checks.push({
        name: "ANTHROPIC_API_KEY",
        pass: !!process.env.ANTHROPIC_API_KEY,
        message: process.env.ANTHROPIC_API_KEY
          ? "Set ✓"
          : "Not set — run: export ANTHROPIC_API_KEY=sk-ant-...",
      });

      // Node version
      const nodeVersion = process.version;
      const nodeMajor = parseInt(nodeVersion.slice(1));
      checks.push({
        name: `Node.js (${nodeVersion})`,
        pass: nodeMajor >= 18,
        message: nodeMajor >= 18 ? "v18+ ✓" : "Requires Node.js 18 or later",
      });

      // git
      checks.push({
        name: "git",
        pass: checkCommand("git"),
        message: checkCommand("git") ? "Found ✓" : "Not found — install git",
      });

      // .anote index
      const indexPath = path.join(cwd, ".anote", "index");
      const hasIndex = fs.existsSync(indexPath);
      checks.push({
        name: "Anote index",
        pass: hasIndex,
        message: hasIndex
          ? `Found at .anote/index ✓`
          : `Not found — run: anote index ${cwd !== process.cwd() ? opts.dir : ""}`,
      });

      // Print results
      console.log(chalk.bold.cyan("\n◆ Anote Doctor\n"));
      let allPassed = true;
      for (const c of checks) {
        const icon = c.pass ? chalk.green("✓") : chalk.red("✗");
        const label = c.pass ? chalk.white(c.name) : chalk.red(c.name);
        const msg = c.pass ? chalk.dim(c.message) : chalk.yellow(c.message);
        console.log(`  ${icon}  ${label}  —  ${msg}`);
        if (!c.pass) allPassed = false;
      }
      console.log();
      if (allPassed) {
        console.log(chalk.green("  All checks passed! You're good to go.\n"));
      } else {
        console.log(chalk.yellow("  Some checks failed. Fix the issues above and re-run.\n"));
        process.exit(1);
      }
    });
}
