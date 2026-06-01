export default function TooltipInfo({ content }: { content: string }) {
  return (
    <div className="group relative inline-flex items-center ml-1.5 cursor-help">
      <span className="flex items-center justify-center w-3.5 h-3.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 text-[10px] font-bold">
        ?
      </span>
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-48 p-2.5 bg-slate-900 border border-slate-700 rounded-lg text-[11px] text-slate-300 shadow-xl z-50 text-center normal-case font-sans tracking-normal opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
        {content}
      </div>
    </div>
  );
}
