import React, { useEffect, useRef } from 'react';
import { Icon } from '@iconify/react';

/**
 * LegacyIcon - A drop-in replacement for the vanilla Iconify span elements.
 * This component extracts data-icon and other data attributes and renders
 * using the Iconify React component.
 * 
 * For new components, prefer using <Icon icon="..." /> directly from @iconify/react
 */
const LegacyIcon = ({
    'data-icon': dataIcon,
    'data-width': dataWidth,
    'data-height': dataHeight,
    className = '',
    style = {},
    icon, // Also support direct icon prop
    width,
    height,
    ...props
}) => {
    const iconName = icon || dataIcon;
    const iconWidth = width || dataWidth;
    const iconHeight = height || dataHeight;

    if (!iconName) {
        console.warn('LegacyIcon: No icon specified');
        return null;
    }

    return (
        <Icon
            icon={iconName}
            className={className}
            width={iconWidth}
            height={iconHeight}
            style={style}
            {...props}
        />
    );
};

export default LegacyIcon;

// Export a custom hook that can be used to replace iconify spans globally
export const useIconifyMigration = () => {
    // This could be used in the future for automated migration
    return null;
};
