# Foci by independent experimental repeat ---------------------------------------
# Formatting example: adapt the input schema and analysis to the actual study.
# Input: Tables/Main_results/01_foci_by_repeat.csv
# Required columns: assay, condition, repeat_id, mean_foci_per_nucleus.
# Each row is ONE independent repeat x assay x condition, not one nucleus.
# This example displays repeat means, with mean +/- SD across repeats.
# It performs no hypothesis test. It assumes the table already contains the
# scientifically agreed within-repeat aggregation and retains valid zero counts.
#
# Terminal: Rscript /path/to/R_scripts/01_foci_by_repeat.R /path/to/results
# RStudio: set results_folder below, then click Source. No packages required.

# 1. EDIT HERE: paths and appearance --------------------------------------------
results_folder <- "."  # In RStudio, replace with your results folder.
plot_title <- "Nuclear foci by experimental repeat"
x_axis_label <- "Condition"
y_axis_label <- "Foci per nucleus"
condition_order <- NULL  # Or specify c("Control", "Treatment") using table labels.
condition_labels <- NULL  # Optional displayed labels in condition_order.
repeat_colours <- c("#2166AC", "#B2182B", "#238B45", "#984EA3")
point_size <- 1.4
text_size <- 1.0
legend_position <- "topright"
y_axis_limits <- NULL  # NULL chooses automatically; alternatively c(0, 150).
figure_width_px <- 2400
figure_height_px <- 1600
figure_resolution <- 220
output_filename <- "01_foci_by_repeat.png"

# An explicit command-line path takes precedence over the RStudio setting.
arguments <- commandArgs(trailingOnly = TRUE)
if (length(arguments) >= 1) {
  results_folder <- arguments[1]
}
results_folder <- normalizePath(results_folder, mustWork = TRUE)
input_file <- file.path(
  results_folder, "Tables", "Main_results", "01_foci_by_repeat.csv"
)
output_folder <- file.path(results_folder, "Graphs")  # Change for styling trials.
dir.create(output_folder, recursive = TRUE, showWarnings = FALSE)

# 2. Read the saved data and check its meaning -----------------------------------
repeat_counts <- read.csv(input_file, check.names = FALSE)
required_columns <- c("assay", "condition", "repeat_id", "mean_foci_per_nucleus")
if (!all(required_columns %in% names(repeat_counts))) {
  stop("The input table is missing a required column; check its data dictionary.")
}
if (nrow(repeat_counts) == 0 || anyNA(repeat_counts[required_columns])) {
  stop("Empty or missing observations require an explicit analysis decision.")
}
if (anyDuplicated(repeat_counts[c("assay", "condition", "repeat_id")])) {
  stop("Expected one row per assay, condition and independent repeat.")
}
if (!is.numeric(repeat_counts$mean_foci_per_nucleus) ||
    any(!is.finite(repeat_counts$mean_foci_per_nucleus)) ||
    any(repeat_counts$mean_foci_per_nucleus < 0)) {
  stop("Counts must be finite, nonnegative numeric values.")
}

# 3. Set plotting order; do not silently drop groups -----------------------------
if (is.null(condition_order)) {
  condition_order <- unique(repeat_counts$condition)
}
if (!setequal(condition_order, unique(repeat_counts$condition))) {
  stop("condition_order must include every condition in the table exactly once.")
}
if (anyDuplicated(condition_order)) {
  stop("condition_order contains a duplicate condition.")
}
if (is.null(condition_labels)) {
  condition_labels <- condition_order
}
if (length(condition_labels) != length(condition_order)) {
  stop("Provide one displayed label per condition.")
}
assays <- unique(repeat_counts$assay)
repeat_names <- unique(repeat_counts$repeat_id)
repeat_palette <- setNames(
  rep(repeat_colours, length.out = length(repeat_names)), repeat_names
)

# 4. Draw one panel per assay ----------------------------------------------------
# Keep individual repeats visible; the number of nuclei is not biological n.
# Wrap device handling in a function so an error still closes the output file.
draw_figure <- function() {
  png(
    filename = file.path(output_folder, output_filename),
    width = figure_width_px,
    height = figure_height_px,
    res = figure_resolution
  )
  on.exit(dev.off(), add = TRUE)
  par(mfrow = c(1, length(assays)), mar = c(7, 5, 4, 1), cex = text_size)

  for (assay_name in assays) {
    assay_counts <- repeat_counts[repeat_counts$assay == assay_name, ]
    group_means <- vapply(condition_order, function(condition_name) {
      mean(assay_counts$mean_foci_per_nucleus[
        assay_counts$condition == condition_name
      ])
    }, numeric(1))
    group_sd <- vapply(condition_order, function(condition_name) {
      sd(assay_counts$mean_foci_per_nucleus[
        assay_counts$condition == condition_name
      ])
    }, numeric(1))
    if (any(!is.finite(group_means)) || any(!is.finite(group_sd))) {
      stop("Each plotted assay/condition needs at least two repeats for SD bars.")
    }

    # Include every observation and the full error bars in the automatic limits.
    panel_limits <- y_axis_limits
    if (is.null(panel_limits)) {
      panel_limits <- range(c(
        0, assay_counts$mean_foci_per_nucleus,
        group_means - group_sd, group_means + group_sd
      ))
      panel_limits[2] <- max(panel_limits[2] * 1.1, 1)
    }
    positions <- seq_along(condition_order)
    plot(
      NA, xlim = c(0.5, length(positions) + 0.5), ylim = panel_limits,
      xaxt = "n", xlab = x_axis_label, ylab = y_axis_label,
      main = paste(plot_title, assay_name, sep = "\n"), bty = "l"
    )
    axis(1, at = positions, labels = condition_labels, las = 2)

    # Offset repeats slightly so overlapping points remain visible.
    offsets <- seq(-0.12, 0.12, length.out = length(repeat_names))
    for (repeat_index in seq_along(repeat_names)) {
      repeat_name <- repeat_names[repeat_index]
      repeat_values <- assay_counts[assay_counts$repeat_id == repeat_name, ]
      points(
        match(repeat_values$condition, condition_order) + offsets[repeat_index],
        repeat_values$mean_foci_per_nucleus,
        pch = 16, cex = point_size, col = repeat_palette[repeat_name]
      )
    }

    # Black markers show equal-weighted repeat means; bars are SD, not SEM or CI.
    segments(positions, group_means - group_sd, positions, group_means + group_sd)
    points(positions, group_means, pch = 95, cex = 2)
    legend(
      legend_position, legend = paste("Repeat", repeat_names),
      col = repeat_palette, pch = 16, bty = "n"
    )
  }
}

# 5. Save the graph; the input measurements remain unchanged ---------------------
draw_figure()
message("Saved graph: ", file.path(output_folder, output_filename))
