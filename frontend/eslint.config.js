import js from '@eslint/js';

export default [
    js.configs.recommended,
    {
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: 'script',
            globals: {
                window: 'readonly',
                document: 'readonly',
                console: 'readonly',
                fetch: 'readonly',
                marked: 'readonly',
                Date: 'readonly',
                Promise: 'readonly',
            },
        },
        rules: {
            'no-unused-vars': 'warn',
            'no-console': 'off',
            eqeqeq: ['error', 'always'],
            curly: ['error', 'all'],
            'no-var': 'error',
            'prefer-const': 'warn',
        },
    },
];
