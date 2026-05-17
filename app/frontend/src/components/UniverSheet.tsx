import { useEffect, useRef } from 'react';
import {
  LocaleType,
  merge,
  Univer,
  UniverInstanceType,
} from '@univerjs/core';
import { defaultTheme } from '@univerjs/design';
import { UniverFormulaEnginePlugin } from '@univerjs/engine-formula';
import { UniverRenderEnginePlugin } from '@univerjs/engine-render';
import { UniverSheetsPlugin } from '@univerjs/sheets';
import { UniverSheetsFormulaPlugin } from '@univerjs/sheets-formula';
import { UniverSheetsUIPlugin } from '@univerjs/sheets-ui';
import { UniverUIPlugin } from '@univerjs/ui';

import DesignZhTW from '@univerjs/design/locale/zh-TW';
import UIZhTW from '@univerjs/ui/locale/zh-TW';
import SheetsZhTW from '@univerjs/sheets/locale/zh-TW';
import SheetsUIZhTW from '@univerjs/sheets-ui/locale/zh-TW';
import SheetsFormulaZhTW from '@univerjs/sheets-formula/locale/zh-TW';

import '@univerjs/design/lib/index.css';
import '@univerjs/ui/lib/index.css';
import '@univerjs/sheets-ui/lib/index.css';

import { COLUMNS, Category, RecordRow } from '../api/records';

interface Props {
  categories: Category[];
  recordsByCategory: Map<string, RecordRow[]>;
}

type CellData = { v: string | number };
type SheetCellMatrix = { [row: string]: { [col: string]: CellData } };

function buildWorkbookData(
  categories: Category[],
  recordsByCategory: Map<string, RecordRow[]>,
) {
  const sheets: { [sheetId: string]: unknown } = {};
  const sheetOrder: string[] = [];

  for (const cat of categories) {
    const recs = recordsByCategory.get(cat.code) || [];
    const sheetId = cat.code;
    sheetOrder.push(sheetId);

    const cellData: SheetCellMatrix = { '0': {} };
    COLUMNS.forEach((c, i) => {
      cellData['0'][String(i)] = { v: c.label };
    });

    recs.forEach((rec, ri) => {
      const row: { [col: string]: CellData } = {};
      COLUMNS.forEach((c, ci) => {
        const v = (rec as unknown as { [k: string]: unknown })[c.key as string];
        if (v === null || v === undefined) return;
        if (typeof v === 'number') row[String(ci)] = { v };
        else if (typeof v === 'boolean') row[String(ci)] = { v: v ? '✓' : '' };
        else row[String(ci)] = { v: String(v) };
      });
      cellData[String(ri + 1)] = row;
    });

    const columnData: { [col: string]: { w: number } } = {};
    COLUMNS.forEach((c, i) => {
      columnData[String(i)] = { w: c.width };
    });

    sheets[sheetId] = {
      id: sheetId,
      name: `${cat.name_zh} (${recs.length})`,
      tabColor: '',
      hidden: 0,
      rowCount: Math.max(recs.length + 5, 100),
      columnCount: COLUMNS.length,
      zoomRatio: 1,
      freeze: { xSplit: 2, ySplit: 1, startRow: 1, startColumn: 2 },
      scrollTop: 0,
      scrollLeft: 0,
      defaultColumnWidth: 100,
      defaultRowHeight: 24,
      mergeData: [],
      cellData,
      rowData: {},
      columnData,
      showGridlines: 1,
      rowHeader: { width: 46, hidden: 0 },
      columnHeader: { height: 20, hidden: 0 },
      rightToLeft: 0,
    };
  }

  return {
    id: 'tmca-records',
    rev: 1,
    name: 'TMCA 總表',
    appVersion: '0.5.5',
    locale: LocaleType.ZH_TW,
    styles: {},
    sheetOrder,
    sheets,
    resources: [],
  };
}

export default function UniverSheet({ categories, recordsByCategory }: Props) {
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
      locale: LocaleType.ZH_TW,
      locales: {
        [LocaleType.ZH_TW]: merge(
          {},
          DesignZhTW,
          UIZhTW,
          SheetsZhTW,
          SheetsUIZhTW,
          SheetsFormulaZhTW,
        ),
      },
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

    u.createUnit(
      UniverInstanceType.UNIVER_SHEET,
      buildWorkbookData(categories, recordsByCategory),
    );
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
