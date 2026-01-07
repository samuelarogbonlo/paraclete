import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:paraclete/core/theme/colors.dart';
import 'package:paraclete/shared/widgets/base_scaffold.dart';

/// Agent dashboard screen placeholder
class AgentDashboardScreen extends ConsumerWidget {
  const AgentDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return BaseScaffold(
      title: 'AI Agents',
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Agent Dashboard',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 8),
          Text(
            'Multi-agent orchestration will be implemented here',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 24),
          _AgentCard(
            name: 'Supervisor',
            status: 'Idle',
            color: AppColors.supervisorColor,
          ),
          _AgentCard(
            name: 'Researcher',
            status: 'Idle',
            color: AppColors.researcherColor,
          ),
          _AgentCard(
            name: 'Coder',
            status: 'Idle',
            color: AppColors.coderColor,
          ),
          _AgentCard(
            name: 'Reviewer',
            status: 'Idle',
            color: AppColors.reviewerColor,
          ),
          _AgentCard(
            name: 'Designer',
            status: 'Idle',
            color: AppColors.designerColor,
          ),
        ],
      ),
    );
  }
}

class _AgentCard extends StatelessWidget {
  final String name;
  final String status;
  final Color color;

  const _AgentCard({
    required this.name,
    required this.status,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: color.withOpacity(0.2),
          child: Icon(Icons.smart_toy, color: color),
        ),
        title: Text(name),
        subtitle: Text('Status: $status'),
        trailing: const Icon(Icons.chevron_right),
      ),
    );
  }
}