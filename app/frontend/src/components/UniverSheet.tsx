import { useEffect, useRef } from 'react';
import { LocaleType, Univer, UniverInstanceType } from '@univerjs/core';
import { defaultTheme } from '@univerjs/design';
import { UniverFormulaEnginePlugin } from '@univerjs/engine-formula';
import { UniverRenderEnginePlugin } from '@univerjs/engine-render';
import { UniverSheetsPlugin } from '@univerjs/sheets';
import { UniverSheetsFormulaPlugin } from '@univerjs/sheets-formula';
import { UniverSheetsUIPlugin } from '@univerjs/sheets-ui';
import { UniverUIPlugin } from '@univerjs/ui';

import '@univerjs/design/lib/index.css';
import '@univerjs/ui/lib/index.css';
import '@univerjs/sheets-ui/lib/index.css';

import { COLUMNS, Category, RecordRow } from '../api/records';

interface Props {
  categories: Category[];
  recordsByCategory: Map<string, RecordRow[]>;
  initialActive?: string;
}

function buildWorkbookData(
  categories: Category[],
  recordsByCategory: Map<string, RecordRow[]>,
) {
  const sheets: Record<string, unknown> = {};
  const sheetOrder: string[] = [];

  for (const cat of categories) {
    const recs = recordsByCategory.get(cat.code) || [];
    const sheetId = cat.code;
    sheetOrder.push(sheetId);

    // 第 1 列：欄位標題
    const cellData: Record<string, Record<string, { v: string | number }>> = {
      '0': {},
    };
    COLUMNS.forEach((c, i) => {
      cellData['0'][String(i)] = { v: c.label };
    });

    // 第 2 列以後：資料
    recs.forEach((rec, ri) => {
      const row: Record<string, { v: string | number }> = {};
      COLUMNS.forEach((c, ci) => {
        const v = (rec as unknown as Record<string, unknown>)[c.key as string];
        if (v === null || v === undefined) return;
        row[String(ci)] =
          typeof v === 'number'
            ? { v }
            : typeof v === 'boolean'
              ? { v: v ? '✓' : '' }
              : { v: String(v) };
      });
      cellData[String(ri + 1)] = row;
    });

    const columnData: Record<string, { w: number }> = {};
    COLUMNS.forEach((c, i) => {
      columnData[String(i)] = { w: c.width };
    });

    sheets[sheetId] = {
      id: sheetId,
      name: `${cat.name_zh} (${recs.length})`,
      rowCount: Math.max(recs.length + 5, 100),
      columnCount: COLUMNS.length,
      cellData,
      columnData,
      freeze: { startRow: 1, startColumn: 2, ySplit: 1, xSplit: 2 },
    };
  }

  return {
    id: 'tmca-records',
    name: 'TMCA 總表',
    appVersion: '0.1',
    locale: LocaleType.ZH_CN,
    sheets,
    sheetOrder,
  };
}

export default function UniverSheet({
  categories,
  recordsByCategory,
  initialActive,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const univerRef = useRef<Univer | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    if (univerRef.current) {
      univerRef.current.dispose();
      univerRef.current = null;
    }

    const u = new Univer({
      theme: defaultTheme,
      locale: LocaleType.ZH_CN,
    });

    u.registerPlugin(UniverRenderEnginePlugin);
    u.registerPlugin(UniverFormulaEnginePlugin);
    u.registerPlugin(UniverUIPlugin, {
      container: containerRef.current,
      header: true,
      toolbar: true,
      footer: true,
    });
    u.registerPlugin(UniverSheetsPlugin);
    u.registerPlugin(UniverSheetsUIPlugin);
    u.registerPlugin(UniverSheetsFormulaPlugin);

    const wbData = buildWorkbookData(categories, recordsByCategory);
    if (initialActive) {
      (wbData as { activeSheet?: string }).activeSheet = initialActive;
    }
    u.createUnit(UniverInstanceType.UNIVER_SHEET, wbData);
    univerRef.current = u;

    return () => {
      u.dispose();
      univerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categories, recordsByCategory]);

  return (
    <div ref={containerRef} className="w-full h-full" style={{ minHeight: 600 }} />
  );
}
