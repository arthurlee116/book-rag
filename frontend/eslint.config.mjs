import js from "@eslint/js";
import nextPlugin from "@next/eslint-plugin-next";
import importPlugin from "eslint-plugin-import";
import jsxA11yPlugin from "eslint-plugin-jsx-a11y";
import reactPlugin from "eslint-plugin-react";
import reactHooksPlugin from "eslint-plugin-react-hooks";
import tsPlugin from "@typescript-eslint/eslint-plugin";

const tsFiles = ["**/*.ts", "**/*.tsx", "**/*.mts", "**/*.cts"];
const reactFiles = ["**/*.jsx", "**/*.tsx"];

const tsConfigs = tsPlugin.configs["flat/recommended"].map((cfg) => {
  // `typescript-eslint/base` and `typescript-eslint/recommended` are global; scope them to TS files.
  if (cfg.files) return cfg;
  return { ...cfg, files: tsFiles };
});

export default [
  {
    ignores: [
      ".next/**",
      "out/**",
      "node_modules/**",
      "eslint.config.mjs",
      "next.config.js",
      "postcss.config.js",
      "tailwind.config.ts",
      "next-env.d.ts"
    ]
  },
  {
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module"
    }
  },
  js.configs.recommended,
  ...tsConfigs,
  {
    ...reactPlugin.configs.flat.recommended,
    files: reactFiles,
    rules: {
      ...reactPlugin.configs.flat.recommended.rules,
      // Next.js uses the automatic JSX runtime; React doesn't need to be in scope.
      "react/react-in-jsx-scope": "off",
      "react/jsx-uses-react": "off",
      // TypeScript replaces prop-types for this project.
      "react/prop-types": "off"
    }
  },
  reactHooksPlugin.configs.flat.recommended,
  nextPlugin.configs["core-web-vitals"],
  {
    plugins: {
      "jsx-a11y": jsxA11yPlugin
    },
    rules: {
      ...jsxA11yPlugin.configs.recommended.rules
    }
  },
  {
    plugins: {
      import: importPlugin
    },
    rules: {
      ...importPlugin.configs.recommended.rules,
      ...importPlugin.configs.typescript?.rules
    },
    settings: {
      "import/resolver": {
        // Supports TS path aliases like `@/*` from tsconfig.
        typescript: {
          project: "./tsconfig.json"
        },
        node: {
          extensions: [".js", ".jsx", ".ts", ".tsx", ".mjs"]
        }
      }
    }
  },
  {
    settings: {
      react: { version: "detect" }
    }
  }
];
