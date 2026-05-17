interface Props {
  value: string | null | undefined;
  size?: number;
}

const COLOR: { [k: string]: string } = {
  '紅': '#C0392B',
  '綠': '#27ae60',
  '灰': '#95A5A6',
};

const LABEL: { [k: string]: string } = {
  '紅': '紅（待續約 / 待核發）',
  '綠': '綠（已續約 / 已核發）',
  '灰': '灰（無關）',
};

export default function StatusDot({ value, size = 12 }: Props) {
  if (!value) return <span className="text-slate-300">—</span>;
  const c = COLOR[value] ?? '#cbd5e1';
  return (
    <span
      className="inline-block align-middle rounded-full"
      style={{ width: size, height: size, background: c }}
      title={LABEL[value] ?? value}
    />
  );
}
