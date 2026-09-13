#!/usr/bin/env node
/** Build a parser-backed callable ledger for first-party JavaScript and HTML templates. */
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { parse as parseJavaScript } from "@babel/parser";
import { parse as parseHtml } from "parse5";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUTPUT = path.join(ROOT, "audit", "frontend_function_inventory.json");
const MARKDOWN = path.join(ROOT, "audit", "FRONTEND_FUNCTION_LEDGER.md");
const SKIP_DIRECTORIES = new Set([
    ".git",
    ".venv",
    ".venv_audit",
    "htmlcov",
    "media",
    "node_modules",
    "staticfiles",
]);
const VENDOR_FILE_PATTERNS = [
    /(^|\/)static\/vendor\//,
    /(^|\/)core\/static\/js\/chart(?:\.umd)?\.min\.js$/,
];
const FUNCTION_TYPES = new Set([
    "FunctionDeclaration",
    "FunctionExpression",
    "ArrowFunctionExpression",
    "ObjectMethod",
    "ClassMethod",
    "ClassPrivateMethod",
]);
const BRANCH_TYPES = new Set([
    "IfStatement",
    "SwitchCase",
    "ConditionalExpression",
    "LogicalExpression",
    "ForStatement",
    "ForInStatement",
    "ForOfStatement",
    "WhileStatement",
    "DoWhileStatement",
    "CatchClause",
]);
const RISK_CALLS = new Map([
    ["eval", "dynamic_execution"],
    ["Function", "dynamic_execution"],
    ["document.write", "document_write"],
    ["document.writeln", "document_write"],
    ["setTimeout", "string_timer_if_non_callable"],
    ["setInterval", "string_timer_if_non_callable"],
]);

function relative(filePath) {
    return path.relative(ROOT, filePath).split(path.sep).join("/");
}

function walkFiles(directory, acceptedExtensions, files = []) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
        if (entry.isDirectory() && SKIP_DIRECTORIES.has(entry.name)) continue;
        const absolute = path.join(directory, entry.name);
        if (entry.isDirectory()) walkFiles(absolute, acceptedExtensions, files);
        else if (acceptedExtensions.has(path.extname(entry.name).toLowerCase())) files.push(absolute);
    }
    return files;
}

function memberName(node) {
    if (!node) return "";
    if (node.type === "Identifier" || node.type === "PrivateName") return node.name || memberName(node.id);
    if (node.type === "ThisExpression") return "this";
    if (node.type === "StringLiteral" || node.type === "NumericLiteral") return String(node.value);
    if (node.type === "MemberExpression" || node.type === "OptionalMemberExpression") {
        const object = memberName(node.object);
        const property = memberName(node.property);
        return object && property ? `${object}.${property}` : property;
    }
    return "";
}

function inferredName(node, parent, ordinal) {
    if (node.id?.name) return node.id.name;
    if (node.key) return memberName(node.key) || `<anonymous#${ordinal}>`;
    if (parent?.type === "VariableDeclarator") return memberName(parent.id) || `<anonymous#${ordinal}>`;
    if (parent?.type === "AssignmentExpression") return memberName(parent.left) || `<anonymous#${ordinal}>`;
    if (parent?.type === "ObjectProperty") return memberName(parent.key) || `<anonymous#${ordinal}>`;
    if (parent?.type === "CallExpression" || parent?.type === "OptionalCallExpression") {
        const callee = memberName(parent.callee);
        return `${callee || "callback"}::<callback#${ordinal}>`;
    }
    return `<anonymous#${ordinal}>`;
}

function childNodes(node) {
    const children = [];
    for (const [key, value] of Object.entries(node)) {
        if (["loc", "start", "end", "errors", "comments", "tokens", "extra"].includes(key)) continue;
        if (Array.isArray(value)) {
            for (const item of value) if (item && typeof item.type === "string") children.push(item);
        } else if (value && typeof value.type === "string") {
            children.push(value);
        }
    }
    return children;
}

function analyzeFunction(node) {
    let branches = 0;
    const risks = new Set();
    const stack = [node.body];
    while (stack.length) {
        const current = stack.pop();
        if (!current || typeof current.type !== "string") continue;
        if (current !== node && FUNCTION_TYPES.has(current.type)) continue;
        if (BRANCH_TYPES.has(current.type)) branches += 1;
        if (current.type === "CallExpression" || current.type === "OptionalCallExpression" || current.type === "NewExpression") {
            const call = memberName(current.callee);
            const risk = RISK_CALLS.get(call);
            if (risk) {
                const isStringTimer = risk === "string_timer_if_non_callable";
                if (!isStringTimer || current.arguments?.[0]?.type === "StringLiteral") risks.add(risk);
            }
        }
        if (current.type === "AssignmentExpression" && /(^|\.)(innerHTML|outerHTML)$/.test(memberName(current.left))) {
            risks.add("html_injection_boundary");
        }
        stack.push(...childNodes(current));
    }
    return { complexityProxy: 1 + branches, riskSignals: [...risks].sort() };
}

function inventoryAst(ast, origin, lineOffset = 0) {
    const functions = [];
    let ordinal = 0;
    const visit = (node, parent, scope) => {
        if (!node || typeof node.type !== "string") return;
        let nextScope = scope;
        if (FUNCTION_TYPES.has(node.type)) {
            ordinal += 1;
            const name = inferredName(node, parent, ordinal);
            const qualname = [...scope, name].join(".");
            const analysis = analyzeFunction(node);
            const line = (node.loc?.start.line || 1) + lineOffset;
            const endLine = (node.loc?.end.line || node.loc?.start.line || 1) + lineOffset;
            functions.push({
                id: `${origin}::${qualname}@${line}`,
                file: origin,
                line,
                end_line: endLine,
                qualname,
                kind: node.type,
                async: Boolean(node.async),
                generator: Boolean(node.generator),
                parameters: node.params?.length || 0,
                complexity_proxy: analysis.complexityProxy,
                risk_signals: analysis.riskSignals,
                static_status: analysis.riskSignals.length ? "static_review_flagged" : "static_review_passed",
                behavioral_status: "not_demonstrated_per_function",
            });
            nextScope = [...scope, name];
        }
        for (const child of childNodes(node)) visit(child, node, nextScope);
    };
    visit(ast.program, null, []);
    return functions;
}

function parseProgram(source, origin, sourceType = "unambiguous", lineOffset = 0) {
    try {
        const ast = parseJavaScript(source, {
            sourceType,
            errorRecovery: true,
            allowAwaitOutsideFunction: true,
            allowReturnOutsideFunction: true,
            plugins: ["jsx", "classProperties", "classPrivateProperties", "classPrivateMethods", "dynamicImport", "optionalChaining", "topLevelAwait"],
        });
        const errors = (ast.errors || []).map((error) => ({
            file: origin,
            line: (error.loc?.line || 1) + lineOffset,
            error: error.message,
        }));
        return { functions: inventoryAst(ast, origin, lineOffset), errors };
    } catch (error) {
        return {
            functions: [],
            errors: [{ file: origin, line: (error.loc?.line || 1) + lineOffset, error: error.message }],
        };
    }
}

function attributes(node) {
    return new Map((node.attrs || []).map((attribute) => [attribute.name.toLowerCase(), attribute.value]));
}

function textContent(node) {
    return (node.childNodes || []).filter((child) => child.nodeName === "#text").map((child) => child.value).join("");
}

function normalizeDjangoTemplateSyntax(source) {
    // Replace template expressions with a valid neutral literal while keeping
    // line breaks and character positions stable for useful diagnostics.
    const neutralize = (match) => {
        let firstToken = true;
        return [...match].map((character) => {
            if (character === "\r" || character === "\n") return character;
            if (firstToken) {
                firstToken = false;
                return "0";
            }
            return " ";
        }).join("");
    };
    const normalizeTag = (match) => {
        const command = match.trim().slice(2, -2).trim().split(/\s+/, 1)[0];
        const controlTags = new Set([
            "if", "elif", "else", "endif", "for", "empty", "endfor",
            "with", "endwith", "block", "endblock", "autoescape", "endautoescape",
            "comment", "endcomment", "filter", "endfilter", "spaceless", "endspaceless",
            "verbatim", "endverbatim",
        ]);
        return controlTags.has(command) ? match.replace(/[^\r\n]/g, " ") : neutralize(match);
    };
    const mask = (value) => value.replace(/[^\r\n]/g, " ");
    const sourceWithStaticBranches = source.replace(
        /\{%\s*if[\s\S]*?%\}([\s\S]*?)\{%\s*else\s*%\}[\s\S]*?\{%\s*endif\s*%\}/g,
        (whole, firstBranch) => {
            const firstStart = whole.indexOf(firstBranch);
            return mask(whole.slice(0, firstStart)) + firstBranch + mask(whole.slice(firstStart + firstBranch.length));
        },
    );
    return sourceWithStaticBranches
        .replace(/\{%[\s\S]*?%\}/g, normalizeTag)
        .replace(/\{\{[\s\S]*?\}\}/g, neutralize)
        .replace(/\{#[\s\S]*?#\}/g, neutralize);
}

function templateSurfaces(filePath) {
    const origin = relative(filePath);
    const source = fs.readFileSync(filePath, "utf8");
    const document = parseHtml(source, { sourceCodeLocationInfo: true });
    const result = { functions: [], errors: [], scripts: [], handlers: [] };
    let scriptIndex = 0;
    let handlerIndex = 0;
    const visit = (node) => {
        const attrs = attributes(node);
        if (node.tagName === "script") {
            scriptIndex += 1;
            const location = node.sourceCodeLocation;
            const line = location?.startLine || 1;
            const type = (attrs.get("type") || "text/javascript").toLowerCase();
            const src = attrs.get("src") || "";
            const script = { id: `${origin}::<script#${scriptIndex}>`, file: origin, line, type, src, status: "" };
            if (src) script.status = "external_reference";
            else if (!["text/javascript", "application/javascript", "module", ""].includes(type)) script.status = "non_javascript_data_block";
            else {
                const code = normalizeDjangoTemplateSyntax(textContent(node));
                script.status = code.trim() ? "parsed" : "empty";
                if (code.trim()) {
                    const parsed = parseProgram(code, script.id, type === "module" ? "module" : "script", line - 1);
                    result.functions.push(...parsed.functions);
                    result.errors.push(...parsed.errors);
                    if (parsed.errors.length) script.status = "parse_error";
                }
            }
            result.scripts.push(script);
        }
        for (const [name, value] of attrs) {
            if (!name.startsWith("on")) continue;
            handlerIndex += 1;
            const line = node.sourceCodeLocation?.attrs?.[name]?.startLine || node.sourceCodeLocation?.startLine || 1;
            const id = `${origin}::<${name}#${handlerIndex}>`;
            const normalizedValue = normalizeDjangoTemplateSyntax(value);
            const parsed = parseProgram(`function __handler__(event) {\n${normalizedValue}\n}`, id, "script", line - 2);
            result.functions.push(...parsed.functions);
            result.errors.push(...parsed.errors);
            result.handlers.push({ id, file: origin, line, event: name.slice(2), status: parsed.errors.length ? "parse_error" : "parsed" });
        }
        for (const child of node.childNodes || []) visit(child);
        if (node.content) visit(node.content);
    };
    visit(document);
    return result;
}

function writeMarkdown(payload) {
    const summary = payload.summary;
    const lines = [
        "# Ledger de funciones JavaScript y plantillas",
        "",
        `Generado: \`${payload.timestamp}\``,
        "",
        "## Resumen",
        "",
        `- Archivos JavaScript propios candidatos: **${summary.javascript_candidates}**`,
        `- Archivos JavaScript parseados: **${summary.javascript_files_parsed}**`,
        `- Archivos vendor excluidos con razon explicita: **${summary.javascript_vendor_exclusions}**`,
        `- Plantillas HTML parseadas: **${summary.template_files_parsed}**`,
        `- Bloques script inline: **${summary.inline_scripts}**`,
        `- Manejadores on* inline: **${summary.inline_event_handlers}**`,
        `- Funciones, metodos y callbacks descubiertos: **${summary.functions}**`,
        `- Funciones sin demostracion conductual individual: **${summary.behaviorally_unverified_functions}**`,
        `- Errores de parseo: **${summary.parse_errors}**`,
        "",
        "> Un parseo correcto y una inspeccion estatica no demuestran comportamiento. Cada error queda enumerado y bloquea una afirmacion de cero omisiones.",
        "",
        "## Errores de parseo",
        "",
        "| Origen | Linea | Error |",
        "|---|---:|---|",
    ];
    for (const error of payload.parse_errors) lines.push(`| \`${error.file}\` | ${error.line} | ${String(error.error).replaceAll("|", "\\|")} |`);
    if (!payload.parse_errors.length) lines.push("| _Ninguno_ | - | - |");
    lines.push("", "## Exclusiones vendor", "", "| Archivo | Razon |", "|---|---|");
    for (const item of payload.vendor_exclusions) lines.push(`| \`${item.file}\` | ${item.reason} |`);
    if (!payload.vendor_exclusions.length) lines.push("| _Ninguna_ | - |");
    lines.push("", "## Limitacion obligatoria", "", "Este ledger garantiza inventario parser-backed dentro del alcance declarado. La verificacion conductual requiere pruebas instrumentadas en navegador y cobertura asociada a cada funcion y rama.", "");
    fs.writeFileSync(MARKDOWN, `${lines.join("\n")}\n`, "utf8");
}

function main() {
    const javascriptCandidates = walkFiles(ROOT, new Set([".js", ".mjs"])).sort();
    const templates = walkFiles(ROOT, new Set([".html", ".htm"])).sort();
    const functions = [];
    const parseErrors = [];
    const vendorExclusions = [];
    const parsedFiles = [];
    const scripts = [];
    const handlers = [];

    for (const filePath of javascriptCandidates) {
        const origin = relative(filePath);
        if (VENDOR_FILE_PATTERNS.some((pattern) => pattern.test(origin))) {
            vendorExclusions.push({ file: origin, reason: "vendored/minified third-party asset" });
            continue;
        }
        const parsed = parseProgram(fs.readFileSync(filePath, "utf8"), origin);
        functions.push(...parsed.functions);
        parseErrors.push(...parsed.errors);
        parsedFiles.push(origin);
    }
    for (const filePath of templates) {
        const result = templateSurfaces(filePath);
        functions.push(...result.functions);
        parseErrors.push(...result.errors);
        scripts.push(...result.scripts);
        handlers.push(...result.handlers);
    }

    const payload = {
        protocol: "PRISLAB_FRONTEND_FUNCTION_INVENTORY_V1",
        timestamp: new Date().toISOString(),
        root: ROOT,
        scope: {
            extensions: [".js", ".mjs", ".html", ".htm"],
            excluded_directories: [...SKIP_DIRECTORIES].sort(),
            note: "Babel parses JavaScript; parse5 discovers template scripts and inline event handlers.",
        },
        summary: {
            javascript_candidates: javascriptCandidates.length,
            javascript_files_parsed: parsedFiles.length,
            javascript_vendor_exclusions: vendorExclusions.length,
            template_files_parsed: templates.length,
            inline_scripts: scripts.length,
            inline_event_handlers: handlers.length,
            functions: functions.length,
            behaviorally_unverified_functions: functions.length,
            parse_errors: parseErrors.length,
            static_review_flagged: functions.filter((item) => item.static_status === "static_review_flagged").length,
        },
        vendor_exclusions: vendorExclusions,
        parse_errors: parseErrors,
        javascript_files: parsedFiles,
        template_files: templates.map(relative),
        scripts,
        handlers,
        functions,
    };

    fs.mkdirSync(path.dirname(OUTPUT), { recursive: true });
    fs.writeFileSync(OUTPUT, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
    writeMarkdown(payload);
    console.log(JSON.stringify(payload.summary));
    return parseErrors.length ? 1 : 0;
}

process.exitCode = main();
