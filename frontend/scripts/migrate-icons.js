/**
 * Script to migrate from vanilla Iconify spans to @iconify/react Icon components
 * Run: node scripts/migrate-icons.js
 */

const fs = require('fs');
const path = require('path');

const srcDir = path.join(__dirname, '..', 'src');

// Files to process
const filesToProcess = [
    'components/dashboard/Workspace.jsx',
    'components/dashboard/Sidebar.jsx',
    'components/dashboard/KnowledgeBase.jsx',
    'components/dashboard/History.jsx',
    'components/dashboard/AgentsSwarm.jsx',
    'components/Dashboard.jsx',
    'components/LandingPage.jsx',
    'App.jsx'
];

// Regex patterns for different span formats
const patterns = [
    // <span className="iconify text-indigo-400" data-icon="lucide:info" style={{ strokeWidth: 1.5 }}></span>
    {
        regex: /<span\s+className={?`([^`]*iconify[^`]*)`}?\s+data-icon={?["']([^"']+)["']}?\s+data-width={?["']?(\d+)["']?}?(?:\s+data-height={?["']?(\d+)["']?}?)?(?:\s+style={{\s*strokeWidth:\s*([\d.]+)\s*}})?><\/span>/g,
        replace: (match, className, icon, width, height, strokeWidth) => {
            const cleanClassName = className.replace('iconify', '').replace(/\s+/g, ' ').trim();
            let props = `icon="${icon}"`;
            if (cleanClassName) props += ` className="${cleanClassName}"`;
            if (width) props += ` width={${width}}`;
            if (height) props += ` height={${height}}`;
            return `<Icon ${props} />`;
        }
    },
    // <span className="iconify text-indigo-400" data-icon="lucide:info"></span>
    {
        regex: /<span\s+className="([^"]*iconify[^"]*)"\s+data-icon="([^"]+)"(?:\s+data-width="(\d+)")?(?:\s+style={{[^}]*}})?><\/span>/g,
        replace: (match, className, icon, width) => {
            const cleanClassName = className.replace('iconify', '').replace(/\s+/g, ' ').trim();
            let props = `icon="${icon}"`;
            if (cleanClassName) props += ` className="${cleanClassName}"`;
            if (width) props += ` width={${width}}`;
            return `<Icon ${props} />`;
        }
    },
    // Catch-all for remaining patterns with data-width as number
    {
        regex: /<span\s+className={?["`]([^"`]*iconify[^"`]*)["`]}?\s+data-icon={?["']([^"']+)["']}?\s+data-width={?(\d+)}?><\/span>/g,
        replace: (match, className, icon, width) => {
            const cleanClassName = className.replace('iconify', '').replace(/\s+/g, ' ').trim();
            let props = `icon="${icon}"`;
            if (cleanClassName) props += ` className="${cleanClassName}"`;
            if (width) props += ` width={${width}}`;
            return `<Icon ${props} />`;
        }
    }
];

// Add Icon import if not present
function addIconImport(content) {
    if (content.includes("import { Icon } from '@iconify/react'")) {
        return content;
    }

    // Find the last import statement
    const importMatch = content.match(/^(import .+? from .+?;?\r?\n)/gm);
    if (importMatch && importMatch.length > 0) {
        const lastImport = importMatch[importMatch.length - 1];
        const importLine = "import { Icon } from '@iconify/react';\n";
        return content.replace(lastImport, lastImport + importLine);
    }

    return "import { Icon } from '@iconify/react';\n" + content;
}

// Process a single file
function processFile(filePath) {
    const fullPath = path.join(srcDir, filePath);

    if (!fs.existsSync(fullPath)) {
        console.log(`Skipping ${filePath} - file not found`);
        return;
    }

    let content = fs.readFileSync(fullPath, 'utf8');
    let originalContent = content;
    let replacements = 0;

    // Apply all patterns
    for (const pattern of patterns) {
        content = content.replace(pattern.regex, (...args) => {
            replacements++;
            return pattern.replace(...args);
        });
    }

    // If we made replacements, add the import
    if (replacements > 0) {
        content = addIconImport(content);
    }

    if (content !== originalContent) {
        fs.writeFileSync(fullPath, content, 'utf8');
        console.log(`✓ Updated ${filePath} (${replacements} replacements)`);
    } else {
        console.log(`- ${filePath} (no changes needed)`);
    }
}

console.log('Migrating Iconify spans to React components...\n');

for (const file of filesToProcess) {
    processFile(file);
}

console.log('\nMigration complete!');
