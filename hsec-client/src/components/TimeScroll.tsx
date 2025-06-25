import { useRef, useEffect, useCallback, useState } from "react";

interface Props {
  startDate: Date
  endDate: Date
  onChange: (d: Date) => void
  dateChange: Date
  steps?: number
  className?: string
}

interface Scale {
  date: Date
  type: 'long' | 'short'
}

const Scale = ({ scale }: { scale: Scale }) => {
  const { date, type } = scale;
  const hh = date.getHours().toString().padStart(2, "0");
  const mm = date.getMinutes().toString().padStart(2, "0");

  return (
    <div className="relative overflow-visible flex flex-col items-center">
      <div className="flex h-5 items-end">
        <div
          className={
            "w-[2px] min-w-[2px] bg-lightpurple rounded-sm " +
            (type === "long" ? "h-5" : "h-3")
          }
        />
      </div>
      <div className="h-5 relative">
        {type === "long" && (
          <span className="absolute text-xs text-lightpurple select-none pointer-events-none left-1/2 -translate-x-1/2">
            {hh}:{mm}
          </span>
        )}
      </div>
    </div>
  );
};

export default function TimeScroll({ startDate, endDate, onChange, dateChange, steps = 5, className = "" }: Props) {
  const [scales, setScales] = useState<Scale[]>([]);
  const [actualEndDate, setActualEndDate] = useState<Date>(endDate);
  const scrollTimeout = useRef<NodeJS.Timeout | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const endOfDay = new Date(endDate);
    endOfDay.setHours(23, 59, 59, 999);
    setActualEndDate(endOfDay);
  }, [endDate])

  const getScales = () => {
    const stepSize = (60 * 60 * 1000) / steps;
    const scales: Scale[] = [];
    for (let d = startDate.getTime(); d <= actualEndDate.getTime(); d += stepSize) {
      const date = new Date(d);
      const type = (date.getMinutes() === 0) ? 'long' : 'short';
      scales.push({ date, type });
    }

    return scales;
  }

  const onScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const scrollLeft = e.currentTarget.scrollLeft;
    const scrollWidth = e.currentTarget.scrollWidth;
    const clientWidth = e.currentTarget.clientWidth;
    const scrollPercentage = scrollLeft / (scrollWidth - clientWidth);

    const totalDuration = actualEndDate.getTime() - startDate.getTime();
    const newDate = new Date(startDate.getTime() + (totalDuration * scrollPercentage));

    if (scrollTimeout.current) {
      clearTimeout(scrollTimeout.current);
    }

    scrollTimeout.current = setTimeout(() => {
      onChange(newDate);
    }, 100);
  }

  useEffect(() => {
    setScales(getScales());
  }, [startDate, actualEndDate]);

  useEffect(() => {
    if (scrollRef.current) {
      const el = scrollRef.current;
      el.scrollLeft = el.scrollWidth - el.clientWidth;
    }
  }, [scales]);

  useEffect(() => {
    if (scrollRef.current && dateChange) {
      const el = scrollRef.current;
      const totalDuration = actualEndDate.getTime() - startDate.getTime();
      const scrollPercentage = (dateChange.getTime() - startDate.getTime()) / totalDuration;
      el.scrollLeft = scrollPercentage * (el.scrollWidth - el.clientWidth);
    }
  }, [dateChange]);

  return (
    <div className={"flex flex-row overflow-y-visible w-full gap-3 items-end relative overflow-x-auto " + className}>
      <div className="absolute top-1 left-1/2 -translate-x-1/2 w-0 h-0 border-x-[5px] border-x-transparent border-t-[8px] border-t-lightblue z-20" />

      <div
        className="px-[50%] flex flex-row gap-3 overflow-x-auto mt-4 hide-scrollbar"
        ref={scrollRef}
        style={{ msOverflowStyle: "none", scrollbarWidth: "none" }}
        onScroll={onScroll}
      >
        {
          scales.map((scale, index) => (
            <Scale key={index} scale={scale} />
          ))
        }
      </div>
    </div>
  )
}
