# Load necessary libraries
pacman::p_load(tidyverse, reshape2, lubridate)

# Read the CSV file
df <- read.csv('sleepICU_monitor_patientID1040.csv')

# Convert timestamp column to POSIXct
timestamp_column <- names(df)[1]
df[[timestamp_column]] <- as.POSIXct(df[[timestamp_column]], tz = "UTC")  # Adjust format if needed

# Separate timestamp and data
data_columns <- names(df)[2:4]

# Reshape data for plotting with ggplot2
df_long <- melt(df, id.vars = timestamp_column, measure.vars = data_columns,
                variable.name = "variable", value.name = "value")

# Convert value to numeric if needed and remove NA values
df_long$value <- as.numeric(as.character(df_long$value))
df_long <- df_long[!is.na(df_long$value), ]

# Define normal ranges for noise, light, and temperature
normal_ranges <- data.frame(
  variable = c("Noise", "Light", "Temperature"),
  min = c(40, 0, 20),
  max = c(55, 100, 24)
)

# Calculate mean values for each variable
mean_values <- aggregate(value ~ variable, data = df_long, FUN = mean)
mean_values$label <- sprintf("%s: %.2f", mean_values$variable, mean_values$value)
print(mean_values)

# Set max_y_value dynamically or use a fixed value
max_y_value <- max(max(df_long$value, na.rm = TRUE), 100)
if (!is.finite(max_y_value)) max_y_value <- 100

# Create the plot
p <- ggplot() +
  geom_line(data = df_long, aes(x = !!sym(timestamp_column), y = value, color = variable)) +
  geom_rect(data = normal_ranges, 
            aes(xmin = min(df_long[[timestamp_column]]), xmax = max(df_long[[timestamp_column]]), 
                ymin = min, ymax = max, fill = variable),
            alpha = 0.1, inherit.aes = FALSE) +
  scale_x_datetime(date_labels = "%H:%M", date_breaks = "30 min") +
  scale_y_continuous(
    breaks = seq(0, max_y_value, by = 5),
    limits = c(0, max_y_value),
    name = "Value",
    sec.axis = sec_axis(~., 
                        breaks = c(normal_ranges$min, normal_ranges$max),
                        labels = c("Noise: 40-55 dB", "Light: 0-100 lux", "Temperature: 20-24 C", 
                                   "Noise: 40-55 dB", "Light: 0-100 lux", "Temperature: 20-24 C"),
                        name = "Normal Ranges")
  ) +
  labs(x = "Time (Hour:Minute)", title = "Patient ID 1040 Sleep ICU Monitor Data Over Time") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1),
        legend.position = "bottom") +
  scale_fill_manual(values = c("Noise" = "red", "Light" = "blue", "Temperature" = "green")) +
  scale_color_manual(values = c("Noise" = "red", "Light" = "blue", "Temperature" = "green")) +
  annotate("rect", 
           xmin = max(df_long[[timestamp_column]]) - 1.3*60*60,
           xmax = max(df_long[[timestamp_column]]),
           ymin = max_y_value - (max_y_value - min(df_long$value)) * 0.2,
           ymax = max_y_value,
           fill = "white", alpha = 0.8) +
  annotate("text", 
           x = max(df_long[[timestamp_column]]) - 1.2*60*60,
           y = max_y_value - (max_y_value - min(df_long$value)) * 0.03,
           label = "Mean values:",
           hjust = 0, vjust = 1, size = 3) +
  annotate("text", 
           x = max(df_long[[timestamp_column]]) - 1.2*60*60,
           y = max_y_value - (max_y_value - min(df_long$value)) * 0.07,
           label = paste(mean_values$label, collapse = "\n"),
           hjust = 0, vjust = 1, size = 3)

# Display the plot
print(p)