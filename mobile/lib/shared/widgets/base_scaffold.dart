import 'package:flutter/material.dart';
import 'package:paraclete/core/theme/colors.dart';

/// Base scaffold widget with common app structure
class BaseScaffold extends StatelessWidget {
  final String? title;
  final Widget body;
  final Widget? floatingActionButton;
  final FloatingActionButtonLocation? floatingActionButtonLocation;
  final List<Widget>? actions;
  final Widget? drawer;
  final Widget? bottomNavigationBar;
  final bool showBackButton;
  final VoidCallback? onBackPressed;
  final Color? backgroundColor;
  final PreferredSizeWidget? bottom;
  final bool extendBodyBehindAppBar;
  final bool resizeToAvoidBottomInset;

  const BaseScaffold({
    super.key,
    this.title,
    required this.body,
    this.floatingActionButton,
    this.floatingActionButtonLocation,
    this.actions,
    this.drawer,
    this.bottomNavigationBar,
    this.showBackButton = true,
    this.onBackPressed,
    this.backgroundColor,
    this.bottom,
    this.extendBodyBehindAppBar = false,
    this.resizeToAvoidBottomInset = true,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: backgroundColor,
      extendBodyBehindAppBar: extendBodyBehindAppBar,
      resizeToAvoidBottomInset: resizeToAvoidBottomInset,
      appBar: title != null
          ? AppBar(
              title: Text(title!),
              actions: actions,
              bottom: bottom,
              automaticallyImplyLeading: showBackButton,
              leading: showBackButton && Navigator.of(context).canPop()
                  ? IconButton(
                      icon: const Icon(Icons.arrow_back),
                      onPressed: onBackPressed ?? () => Navigator.pop(context),
                    )
                  : null,
            )
          : null,
      body: body,
      floatingActionButton: floatingActionButton,
      floatingActionButtonLocation: floatingActionButtonLocation,
      drawer: drawer,
      bottomNavigationBar: bottomNavigationBar,
    );
  }
}

/// Safe area scaffold wrapper
class SafeScaffold extends StatelessWidget {
  final String? title;
  final Widget body;
  final Widget? floatingActionButton;
  final List<Widget>? actions;
  final Widget? bottomNavigationBar;
  final bool top;
  final bool bottom;
  final bool left;
  final bool right;

  const SafeScaffold({
    super.key,
    this.title,
    required this.body,
    this.floatingActionButton,
    this.actions,
    this.bottomNavigationBar,
    this.top = true,
    this.bottom = true,
    this.left = true,
    this.right = true,
  });

  @override
  Widget build(BuildContext context) {
    return BaseScaffold(
      title: title,
      actions: actions,
      floatingActionButton: floatingActionButton,
      bottomNavigationBar: bottomNavigationBar,
      body: SafeArea(
        top: top,
        bottom: bottom,
        left: left,
        right: right,
        child: body,
      ),
    );
  }
}

/// Gradient scaffold with custom background
class GradientScaffold extends StatelessWidget {
  final String? title;
  final Widget body;
  final Gradient gradient;
  final List<Widget>? actions;
  final Widget? floatingActionButton;

  const GradientScaffold({
    super.key,
    this.title,
    required this.body,
    required this.gradient,
    this.actions,
    this.floatingActionButton,
  });

  @override
  Widget build(BuildContext context) {
    return BaseScaffold(
      title: title,
      actions: actions,
      floatingActionButton: floatingActionButton,
      extendBodyBehindAppBar: true,
      body: Container(
        decoration: BoxDecoration(gradient: gradient),
        child: SafeArea(child: body),
      ),
    );
  }
}

/// Scrollable scaffold for long content
class ScrollableScaffold extends StatelessWidget {
  final String? title;
  final List<Widget> children;
  final EdgeInsetsGeometry? padding;
  final ScrollPhysics? physics;
  final List<Widget>? actions;
  final Widget? floatingActionButton;
  final bool addAutomaticKeepAlives;
  final CrossAxisAlignment crossAxisAlignment;

  const ScrollableScaffold({
    super.key,
    this.title,
    required this.children,
    this.padding,
    this.physics,
    this.actions,
    this.floatingActionButton,
    this.addAutomaticKeepAlives = true,
    this.crossAxisAlignment = CrossAxisAlignment.start,
  });

  @override
  Widget build(BuildContext context) {
    return BaseScaffold(
      title: title,
      actions: actions,
      floatingActionButton: floatingActionButton,
      body: SingleChildScrollView(
        padding: padding ?? const EdgeInsets.all(16),
        physics: physics ?? const BouncingScrollPhysics(),
        child: Column(
          crossAxisAlignment: crossAxisAlignment,
          children: children,
        ),
      ),
    );
  }
}

/// Tab scaffold for tabbed navigation
class TabScaffold extends StatelessWidget {
  final String? title;
  final List<Tab> tabs;
  final List<Widget> tabViews;
  final List<Widget>? actions;
  final TabController? controller;
  final bool isScrollable;

  const TabScaffold({
    super.key,
    this.title,
    required this.tabs,
    required this.tabViews,
    this.actions,
    this.controller,
    this.isScrollable = false,
  });

  @override
  Widget build(BuildContext context) {
    assert(tabs.length == tabViews.length, 'Tabs and views must have same length');

    return DefaultTabController(
      length: tabs.length,
      child: BaseScaffold(
        title: title,
        actions: actions,
        bottom: TabBar(
          controller: controller,
          tabs: tabs,
          isScrollable: isScrollable,
          indicatorColor: AppColors.primary,
          labelColor: AppColors.primary,
          unselectedLabelColor: AppColors.neutral500,
        ),
        body: TabBarView(
          controller: controller,
          children: tabViews,
        ),
      ),
    );
  }
}

/// Sliver scaffold for complex scrolling
class SliverScaffold extends StatelessWidget {
  final String title;
  final List<Widget> slivers;
  final Widget? flexibleSpace;
  final double? expandedHeight;
  final bool floating;
  final bool pinned;
  final bool snap;
  final List<Widget>? actions;

  const SliverScaffold({
    super.key,
    required this.title,
    required this.slivers,
    this.flexibleSpace,
    this.expandedHeight,
    this.floating = false,
    this.pinned = true,
    this.snap = false,
    this.actions,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            title: Text(title),
            floating: floating,
            pinned: pinned,
            snap: snap,
            expandedHeight: expandedHeight,
            flexibleSpace: flexibleSpace,
            actions: actions,
          ),
          ...slivers,
        ],
      ),
    );
  }
}