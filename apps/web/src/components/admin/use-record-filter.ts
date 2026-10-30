import { useState } from "react";

type FilterOptions<T> = { rows: T[]; fields: readonly (keyof T)[]; statusField?: keyof T };

export function useRecordFilter<T>({ rows, fields, statusField }: FilterOptions<T>) {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const needle = search.trim().toLocaleLowerCase();
  const matches = rows.filter((row) => {
    if (statusField && status !== "all" && String(row[statusField]) !== status) return false;
    return !needle || fields.some((field) => String(row[field] ?? "").toLocaleLowerCase().includes(needle));
  });
  function reset() { setSearch(""); setStatus("all"); }
  return { rows: matches, search, status, filtered: Boolean(needle) || status !== "all",
    onSearch: setSearch, onStatus: setStatus, onReset: reset };
}
