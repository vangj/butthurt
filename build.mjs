import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "fs-extra";
import fg from "fast-glob";
import postcss from "postcss";
import cssnano from "cssnano";
import { transform as transformJs } from "esbuild";
import { minify as minifyHtml } from "html-minifier-terser";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SOURCE_DIR = path.resolve(__dirname, "www");
const OUTPUT_DIR = path.resolve(__dirname, "www-optimized");

const htmlMinifyOptions = {
  collapseBooleanAttributes: true,
  collapseWhitespace: true,
  decodeEntities: true,
  minifyCSS: true,
  minifyJS: true,
  removeComments: true,
  removeEmptyAttributes: true,
  removeRedundantAttributes: true,
  removeScriptTypeAttributes: true,
  removeStyleLinkTypeAttributes: true,
  sortAttributes: true,
  sortClassName: true,
  useShortDoctype: true
};

async function optimizeJavaScript() {
  const files = await fg("**/*.js", { cwd: SOURCE_DIR, onlyFiles: true });
  await Promise.all(
    files.map(async (relativePath) => {
      const sourcePath = path.join(SOURCE_DIR, relativePath);
      const destinationPath = path.join(OUTPUT_DIR, relativePath);
      const code = await fs.readFile(sourcePath, "utf8");
      const result = await transformJs(code, {
        loader: "js",
        format: "esm",
        minify: true,
        legalComments: "none",
        target: "es2019",
        sourcefile: path.relative(process.cwd(), sourcePath)
      });
      await fs.outputFile(destinationPath, result.code);
    })
  );
}

async function optimizeCss() {
  const processor = postcss([cssnano({ preset: "default" })]);
  const files = await fg("**/*.css", { cwd: SOURCE_DIR, onlyFiles: true });
  await Promise.all(
    files.map(async (relativePath) => {
      const sourcePath = path.join(SOURCE_DIR, relativePath);
      const destinationPath = path.join(OUTPUT_DIR, relativePath);
      const css = await fs.readFile(sourcePath, "utf8");
      const result = await processor.process(css, {
        from: sourcePath,
        to: destinationPath
      });
      await fs.outputFile(destinationPath, result.css);
    })
  );
}

async function optimizeHtml() {
  const files = await fg("**/*.html", { cwd: SOURCE_DIR, onlyFiles: true });
  await Promise.all(
    files.map(async (relativePath) => {
      const sourcePath = path.join(SOURCE_DIR, relativePath);
      const destinationPath = path.join(OUTPUT_DIR, relativePath);
      const html = await fs.readFile(sourcePath, "utf8");
      const minified = await minifyHtml(html, htmlMinifyOptions);
      await fs.outputFile(destinationPath, minified);
    })
  );
}

async function main() {
  if (!(await fs.pathExists(SOURCE_DIR))) {
    throw new Error(`Source directory not found: ${SOURCE_DIR}`);
  }

  await fs.emptyDir(OUTPUT_DIR);
  await fs.copy(SOURCE_DIR, OUTPUT_DIR, { overwrite: true });

  await Promise.all([optimizeJavaScript(), optimizeCss(), optimizeHtml()]);

  console.log(`Optimized assets written to ${OUTPUT_DIR}`);
}

main().catch((error) => {
  console.error("Build failed:\n", error);
  process.exitCode = 1;
});
