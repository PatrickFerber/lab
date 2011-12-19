import logging
import sys

try:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
except ImportError, err:
    logging.error('matplotlib could not be found: %s' % err)
    sys.exit(1)

from absolute import AbsoluteReport
from lab import tools


class ScatterPlotReport(AbsoluteReport):
    def __init__(self, *args, **kwargs):
        AbsoluteReport.__init__(self, 'problem', *args, **kwargs)
        assert len(self.attributes) == 1, self.attributes

    def write_plot(self, attribute, filename):
        table = self._get_table(attribute)
        cfg1, cfg2 = table.cols
        columns = table.get_columns()
        assert len(columns[cfg1]) == len(columns[cfg2]), columns

        # It may be the case that no values are found
        try:
            max_value = max(columns[cfg1] + columns[cfg2])
        except ValueError:
            pass

        if max_value is None or max_value <= 0:
            logging.info('Found no valid datapoints for the plot.')
            print table
            sys.exit()

        # Make the value bigger to separate it from normal values
        missing_val = tools.round_to_next_power_of_ten(max_value * 10)

        values1 = []
        values2 = []
        for val1, val2 in zip(columns[cfg1], columns[cfg2]):
            if val1 is None and val2 is None:
                continue
            if val1 is None:
                val1 = missing_val
            if val2 is None:
                val2 = missing_val
            values1.append(val1)
            values2.append(val2)

        plot_size = missing_val * 1.25

        # Create a figure with size 6 x 6 inches
        fig = Figure(figsize=(10, 10))

        # Create a canvas and add the figure to it
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)

        # Make a descriptive title and set axis labels
        title = ' '.join([attribute, 'by', self.resolution])
        ax.set_title(title, fontsize=14)
        ax.set_xlabel(cfg1, fontsize=12)
        ax.set_ylabel(cfg2, fontsize=12)

        # Display grid
        ax.grid(b=True, linestyle='-', color='0.75')

        # Generate the scatter plot
        ax.scatter(values1, values2, s=20, marker='o', c='r');

        # Plot a diagonal black line. Starting at (0,0) often raises errors.
        ax.plot([0.001, plot_size], [0.001, plot_size], 'k')

        linear_attributes = ['cost', 'coverage', 'plan_length']
        if attribute not in linear_attributes:
            logging.info('Using logarithmic scaling')
            ax.set_xscale('symlog')
            ax.set_yscale('symlog')

        ax.set_xlim(0, plot_size)
        ax.set_ylim(0, plot_size)

        # We do not want the default formatting that gives zeros a special font
        for axis in (ax.xaxis, ax.yaxis):
            formatter = axis.get_major_formatter()
            old_format_call = formatter.__call__
            def new_format_call(x, pos):
                if x == 0:
                    return 0
                if x == missing_val:
                    return 'Missing' # '$\mathdefault{None^{\/}}$' no effect
                return old_format_call(x, pos)
            formatter.__call__ = new_format_call

        # Save the generated scatter plot to a PNG file
        canvas.print_figure(filename, dpi=100)

    def write(self):
        assert len(self.get_configs()) == 2, self.get_configs()

        filename = self.get_filename()
        if not filename.endswith('.png'):
            filename += '.png'
        self.write_plot(self.attributes[0], filename)
        logging.info('Wrote file://%s' % filename)