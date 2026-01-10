const fs = require('fs');

const file = process.argv[2];
let content = fs.readFileSync(file, 'utf8');

// Pattern 1: <span className="iconify ..." data-icon="..." style={{ strokeWidth: N }}></span>
content = content.replace(
    /<span className="iconify ([^"]*)" data-icon="([^"]+)"(?:\s+data-width="(\d+)")?(?:\s+style=\{\{ strokeWidth: [\d.]+ \}\})?><\/span>/g,
    (match, className, icon, width) => {
        let result = `<Icon icon="${icon}"`;
        if (className.trim()) result += ` className="${className.trim()}"`;
        if (width) result += ` width={${width}}`;
        result += ' />';
        return result;
    }
);

// Pattern 2: <span className={`iconify ...`} data-icon="..." data-width="N"></span>
content = content.replace(
    /<span className=\{`iconify ([^`]*)`\} data-icon=\{?["']?([^"'\}]+)["']?\}?(?:\s+data-width=\{?["']?(\d+)["']?\}?)?(?:\s+style=\{\{ strokeWidth: [\d.]+ \}\})?><\/span>/g,
    (match, className, icon, width) => {
        let result = `<Icon icon="${icon}"`;
        if (className.trim()) result += ` className={\`${className.trim()}\`}`;
        if (width) result += ` width={${width}}`;
        result += ' />';
        return result;
    }
);

// Pattern 3: <span className={`iconify ...`} data-icon="..." data-width={N}></span>
content = content.replace(
    /<span className=\{`iconify ([^`]*)`\} data-icon="([^"]+)" data-width=\{(\d+)\}><\/span>/g,
    (match, className, icon, width) => {
        let result = `<Icon icon="${icon}"`;
        if (className.trim()) result += ` className={\`${className.trim()}\`}`;
        if (width) result += ` width={${width}}`;
        result += ' />';
        return result;
    }
);

// Pattern 4: <span className="iconify ..." data-icon={...} data-width="N"></span>
content = content.replace(
    /<span className="iconify ([^"]*)" data-icon=\{([^\}]+)\} data-width="(\d+)"(?:\s+style=\{\{ strokeWidth: [\d.]+ \}\})?><\/span>/g,
    (match, className, iconVar, width) => {
        let result = `<Icon icon={${iconVar}}`;
        if (className.trim()) result += ` className="${className.trim()}"`;
        if (width) result += ` width={${width}}`;
        result += ' />';
        return result;
    }
);

// Pattern 5: Handle remaining cases with title attribute
content = content.replace(
    /<span className="iconify ([^"]*)" data-icon="([^"]+)"(?:\s+style=\{\{ strokeWidth: [\d.]+ \}\})? title="([^"]+)"><\/span>/g,
    (match, className, icon, title) => {
        let result = `<Icon icon="${icon}"`;
        if (className.trim()) result += ` className="${className.trim()}"`;
        result += ` title="${title}"`;
        result += ' />';
        return result;
    }
);

fs.writeFileSync(file, content);
console.log('Done processing', file);
