import js from "@eslint/js";
import reactPlugin from "eslint-plugin-react";

export default [
  js.configs.recommended,
  {
    files: ["**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        window: "readonly",
        document: "readonly",
        EventSource: "readonly",
        fetch: "readonly",
        URL: "readonly",
        localStorage: "readonly",
        crypto: "readonly",
        HTMLElement: "readonly",
      },
    },
    plugins: {
      react: reactPlugin,
    },
    settings: {
      react: {
        version: "detect",
      },
    },
    rules: {
      "react/react-in-jsx-scope": "off",
      "react/jsx-uses-vars": "error",
      "no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
    },
  },
];
