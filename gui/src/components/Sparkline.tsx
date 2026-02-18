import React, { useMemo } from 'react';

interface SparklineProps {
    data: number[];
    color: string;
    width?: number;
    height?: number;
}

const Sparkline: React.FC<SparklineProps> = ({ data = [], color, width = 120, height = 40 }) => {
    const points = useMemo(() => {
        if (data.length === 0) return "";
        const max = Math.max(...data, 100); // Scale to at least 100% or max
        const min = 0;
        const step = width / (data.length - 1 || 1);

        return data.map((val, i) => {
            const x = i * step;
            const y = height - ((val - min) / (max - min)) * height;
            return `${x},${y}`;
        }).join(" ");
    }, [data, width, height]);

    return (
        <svg width={width} height={height} style={{ overflow: 'visible' }}>
            <polyline
                fill="none"
                stroke={color}
                strokeWidth="2"
                points={points}
                strokeLinecap="round"
                vectorEffect="non-scaling-stroke"
            />
            <circle cx={(data.length - 1) * (width / (data.length - 1 || 1))} cy={height - ((data[data.length - 1] - 0) / (Math.max(...data, 100) - 0)) * height} r="3" fill={color} />
        </svg>
    );
};

export default Sparkline;
