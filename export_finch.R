# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
#
# birdsong-mi-decay-test, AMENDMENT-1 (house-finch loader), step 1 of 2.
# Exports, with base R only, the columns the registered stage-2 test needs from the authors'
# own R data files (Youngblood 2024, Zenodo 10786105, CC BY 4.0):
#   processed_data.RData -> processed_data$data: individual, song, cluster_2, cluster_3, cluster_4
#                           (row order kept: the authors' MI code uses this row order as is)
#   mi_data.RData        -> mi_data[[g]] (g = 1..3 = deep split 2..4): dist, mi_raw, mi_base
# Written to <data_dir>/finch_rows.tsv and <data_dir>/their_mi_<g>.tsv. Only structure (column
# names, row counts) goes to <out_dir>/export_report.txt.
# Usage: Rscript export_finch.R <data_dir> <out_dir>

args <- commandArgs(trailingOnly = TRUE)
data_dir <- args[1]
out_dir <- args[2]
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
report <- file.path(out_dir, "export_report.txt")
say <- function(...) {
  line <- paste0(...)
  cat(line, "\n", sep = "")
  cat(line, "\n", sep = "", file = report, append = TRUE)
}
if (file.exists(report)) file.remove(report)

load(file.path(data_dir, "processed_data.RData"))
if (!exists("processed_data")) {
  say("EXPORT STOP: object processed_data not found")
  quit(status = 3)
}
d <- processed_data$data
say("processed_data$data class: ", paste(class(d), collapse = ","), "; rows: ", nrow(d))
say("columns: ", paste(names(d), collapse = ","))
need <- c("individual", "song", "cluster_2", "cluster_3", "cluster_4")
miss <- setdiff(need, names(d))
if (length(miss) > 0) {
  say("EXPORT STOP: missing columns ", paste(miss, collapse = ","))
  quit(status = 3)
}
clean <- function(x) gsub("[\t\r\n]", " ", as.character(x))
rows <- data.frame(row = seq_len(nrow(d)),
                   individual = clean(d$individual),
                   song = clean(d$song),
                   c2 = clean(d$cluster_2),
                   c3 = clean(d$cluster_3),
                   c4 = clean(d$cluster_4),
                   stringsAsFactors = FALSE)
write.table(rows, file.path(data_dir, "finch_rows.tsv"), sep = "\t", quote = FALSE,
            row.names = FALSE, na = "NA")
say("finch_rows.tsv rows: ", nrow(rows))

load(file.path(data_dir, "mi_data.RData"))
if (!exists("mi_data")) {
  say("EXPORT STOP: object mi_data not found")
  quit(status = 3)
}
say("mi_data class: ", paste(class(mi_data), collapse = ","), "; length: ", length(mi_data))
for (g in seq_along(mi_data)) {
  m <- mi_data[[g]]
  if (!all(c("dist", "mi_raw", "mi_base") %in% names(m))) {
    say("EXPORT STOP: mi_data[[", g, "]] lacks dist/mi_raw/mi_base; has ",
        paste(names(m), collapse = ","))
    quit(status = 3)
  }
  out <- data.frame(dist = m$dist, mi_raw = sprintf("%.17g", m$mi_raw),
                    mi_base = sprintf("%.17g", m$mi_base), stringsAsFactors = FALSE)
  write.table(out, file.path(data_dir, paste0("their_mi_", g, ".tsv")), sep = "\t",
              quote = FALSE, row.names = FALSE)
  say("their_mi_", g, ".tsv rows: ", nrow(out))
}
say("EXPORT OK")
