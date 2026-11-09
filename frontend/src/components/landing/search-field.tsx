"use client";

import { useState, type FormEvent } from "react";
import { SearchIcon } from "@/components/icons";

/**
 * Hero search field (56 px high) with example question chips.
 * No backend yet — chips fill the field, submitting is a no-op.
 */
export default function SearchField({
  placeholder,
  buttonLabel,
  examplesLabel,
  chips,
}: {
  placeholder: string;
  buttonLabel: string;
  examplesLabel: string;
  chips: string[];
}) {
  const [value, setValue] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
  }

  return (
    <div>
      <form role="search" onSubmit={handleSubmit} className="flex gap-2">
        <label htmlFor="hero-search" className="sr-only">
          {placeholder}
        </label>
        <input
          id="hero-search"
          type="text"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder={placeholder}
          className="h-14 w-full rounded-lg border border-stroke bg-white px-4 text-base"
        />
        <button type="submit" className="btn-primary h-14 shrink-0 px-6 text-base">
          <SearchIcon className="h-4 w-4" />
          {buttonLabel}
        </button>
      </form>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="text-sm text-ink-secondary">{examplesLabel}</span>
        {chips.map((chip) => (
          <button
            key={chip}
            type="button"
            onClick={() => setValue(chip)}
            className="rounded-md border border-stroke bg-white px-3 py-1.5 text-sm text-ink-secondary transition-colors duration-150 hover:border-primary hover:text-primary"
          >
            {chip}
          </button>
        ))}
      </div>
    </div>
  );
}
