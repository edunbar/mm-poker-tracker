module.exports = {
  extends: [
    'react-app',
    'react-app/jest'
  ],
  rules: {
    // Existing rules
    '@typescript-eslint/no-unused-vars': ['error', {
      argsIgnorePattern: '^_',
      varsIgnorePattern: '^_',
      ignoreRestSiblings: true
    }],
    'no-unused-vars': 'off',
    'prefer-const': 'error',
    'no-var': 'error',

    // TypeScript-specific rules (basic ones that don't require type info)
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/no-non-null-assertion': 'warn',
    '@typescript-eslint/no-inferrable-types': 'error',

    // Code quality and consistency
    'eqeqeq': ['error', 'always'],
    'no-console': 'error',
    'no-debugger': 'error',
    'no-duplicate-imports': 'error',
    'no-return-await': 'error',
    'no-unreachable': 'error',
    'no-unused-expressions': 'error',

    // React-specific improvements
    'react/jsx-no-duplicate-props': 'error',
    'react/jsx-no-undef': 'error',
    'react/jsx-uses-react': 'off', // Not needed with new JSX transform
    'react/jsx-uses-vars': 'error',
    'react/no-direct-mutation-state': 'error',
    'react/no-unused-state': 'error',
    'react/prefer-stateless-function': 'warn',
    'react/self-closing-comp': 'error',

    // Security-related rules
    'no-eval': 'error',
    'no-implied-eval': 'error',
    'no-script-url': 'error',

    // Performance and best practices
    'react-hooks/exhaustive-deps': 'warn',
    'react-hooks/rules-of-hooks': 'error',

    // Import organization
    'import/no-duplicates': 'error',
    'import/order': ['error', {
      groups: [
        'builtin',
        'external',
        'internal',
        'parent',
        'sibling',
        'index'
      ],
      'newlines-between': 'never',
      alphabetize: {
        order: 'asc',
        caseInsensitive: true
      }
    }]
  }
};